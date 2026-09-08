"""Known sampling units and an analytic observation model, not a clinical model."""

from __future__ import annotations

import math
import random
from copy import deepcopy
from dataclasses import asdict

from conformal_pathways.data import Observation, Sample, validate_samples
from conformal_pathways.data.splits import validate_splits


def generate_trial(workflow_name, config, scenario, seed):
    rng = random.Random(seed)
    samples, splits = [], {key: [] for key in ("train", "cal", "test")}
    for split in splits:
        for group in range(scenario[f"{split}_groups"]):
            gid = f"{split}_{group}"
            if workflow_name == "dr_workflow":
                label = rng.choices(range(5), weights=config["dr_prior"])[0]
                dme = rng.random() < config["dr_dme_probability"][label]
                center = config["dr_signal_centers"][label]
                sd = config["dr_signal_sd"]
            elif workflow_name == "glaucoma_workflow":
                label = int(rng.random() < config["glaucoma_high_probability"])
                center = config["glaucoma_signal_centers"][label]
                sd = config["glaucoma_signal_sd"]
            else:
                raise ValueError("unsupported workflow")
            for member in range(config["members_per_group"]):
                sid = f"{gid}_{member}"
                signal = rng.gauss(center, sd)
                labels = (
                    {"dr_severity": label, "dme_positive": dme}
                    if workflow_name == "dr_workflow"
                    else {"glaucoma_risk": "high" if label else "low"}
                )
                if rng.random() < scenario["missing_probability"]:
                    labels.pop(
                        "dme_positive" if workflow_name == "dr_workflow" else "glaucoma_risk"
                    )
                samples.append(
                    Sample(
                        sid,
                        "synthetic",
                        None,
                        labels,
                        {"patient_id": gid, "group_provenance": "known_generator_group"},
                        {"signal": Observation(signal, source="synthetic_entry_measurement")},
                    )
                )
                splits[split].append(sid)
    validate_splits(samples, splits)
    return samples, splits


class KnownSignalPredictor:
    """Posterior under the specified generator, using one entry measurement only."""

    def __init__(self, workflow_name, config):
        self.workflow_name = workflow_name
        if workflow_name == "dr_workflow":
            self.class_values = list(range(5))
            self.prior = list(config["dr_prior"])
            self.centers = list(config["dr_signal_centers"])
            self.sd = config["dr_signal_sd"]
            self.label_key = "dr_severity"
        else:
            self.class_values = ["low", "high"]
            p = config["glaucoma_high_probability"]
            self.prior = [1 - p, p]
            self.centers = list(config["glaucoma_signal_centers"])
            self.sd = config["glaucoma_signal_sd"]
            self.label_key = "glaucoma_risk"

    def fit(self, samples):
        validate_samples(samples)
        self.training_groups = frozenset(s.group_id() for s in samples)
        self.training_ids = frozenset(s.sample_id for s in samples)

    def predict_proba(self, inputs):
        result = []
        for sample in inputs:
            x = sample.observed_values()["signal"]
            values = [
                math.log(p) - 0.5 * ((x - c) / self.sd) ** 2
                for p, c in zip(self.prior, self.centers, strict=True)
            ]
            maximum = max(values)
            probabilities = [math.exp(v - maximum) for v in values]
            total = sum(probabilities)
            result.append(
                {str(k): p / total for k, p in zip(self.class_values, probabilities, strict=True)}
            )
        return result


class FrozenPredictor:
    """Reuse one fitted model and exact entry-input predictions across paired variants."""

    def __init__(self, predictor, training, all_samples):
        predictor.fit(training)
        self.base = predictor
        self._training = {s.sample_id: asdict(s) for s in training}
        inputs = [s.prediction_input() for s in all_samples]
        self._inputs = {s.sample_id: s for s in inputs}
        values = predictor.predict_proba(inputs)
        if len(values) != len(inputs):
            raise ValueError("predictor output count mismatch")
        self._predictions = dict(zip(self._inputs, values, strict=True))

    def __getattr__(self, key):
        return getattr(self.base, key)

    def fit(self, samples):
        validate_samples(samples)
        if {s.sample_id: asdict(s) for s in samples} != self._training:
            raise ValueError("frozen model training records changed")

    def predict_proba(self, inputs):
        values = []
        for sample in inputs:
            if sample != self._inputs.get(sample.sample_id):
                raise ValueError("frozen prediction input is unknown or changed")
            values.append(deepcopy(self._predictions[sample.sample_id]))
        return values

    def prediction_records(self):
        return deepcopy(self._predictions)

    def provenance(self):
        from .provenance import digest

        return {
            "model_class": f"{type(self.base).__module__}.{type(self.base).__qualname__}",
            "training_records_sha256": digest(self._training),
            "predictions_sha256": digest(self._predictions),
            "class_values": self.class_values,
            "config": {
                k: getattr(self.base, k, None) for k in ("C", "smoothing", "prior", "centers", "sd")
            },
            "embedding_metadata": getattr(self.base, "cache_metadata", None),
        }

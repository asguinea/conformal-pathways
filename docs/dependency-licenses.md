# Dependency license inventory

Reviewed on 2026-09-09 against all 64 external package/version resolutions in
`uv.lock`, including alternative Python and optional platform resolutions.
The [machine-readable inventory](dependency-licenses.json) records PyPI metadata
identities, license fields, and supplemental wheel-license entry hashes where
metadata was absent. Only the necessary ZIP directory/license entries were
fetched for those checks; GPU libraries were not downloaded or bundled.

This repository distributes project source and research outputs. It does not
redistribute dependencies, their binary libraries, model weights, or a container
image. Dependencies retain their own terms independently of Apache-2.0.
Permissive Python dependencies dominate the core environment; optional NVIDIA
components carry additional restrictions. `cuda-toolkit` is a metapackage with
no declared license in its metadata/wheel; its components' terms still apply.
Do not describe an optional GPU environment as wholly Apache-licensed or treat
this inventory as clearance to redistribute its binaries.

No known advisory was returned in PyPI version metadata for the current 64
resolutions at review time. This is a point-in-time database check, not proof of
absence of vulnerabilities. The release upgraded setuptools to 83.0.0 to address
[a source-archive exclusion issue](https://github.com/advisories/GHSA-h35f-9h28-mq5c).
Historical experiment locks retain their original build dependency for exact
reproduction; they are not current deployment recommendations.

| Package | Locked version | License / reviewed terms | Primary source |
| --- | --- | --- | --- |
| build | 1.6.0 | MIT | [Version metadata](https://pypi.org/pypi/build/1.6.0/json) |
| cloudpickle | 3.1.2 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/cloudpickle/3.1.2/json) |
| colorama | 0.4.6 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/colorama/0.4.6/json) |
| contourpy | 1.3.3 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/contourpy/1.3.3/json) |
| cuda-bindings | 13.3.1 | LicenseRef-NVIDIA-SOFTWARE-LICENSE | [Version metadata](https://pypi.org/pypi/cuda-bindings/13.3.1/json) |
| cuda-pathfinder | 1.8.1 | Apache-2.0 | [Version metadata](https://pypi.org/pypi/cuda-pathfinder/1.8.1/json) |
| cuda-toolkit | 13.0.3.0 | Metapackage; no license declared in metadata or wheel; component terms apply | [Version metadata](https://pypi.org/pypi/cuda-toolkit/13.0.3.0/json) |
| cycler | 0.12.1 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/cycler/0.12.1/json) |
| filelock | 3.32.5 | MIT | [Version metadata](https://pypi.org/pypi/filelock/3.32.5/json) |
| fonttools | 4.64.0 | MIT | [Version metadata](https://pypi.org/pypi/fonttools/4.64.0/json) |
| fsspec | 2026.7.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/fsspec/2026.7.0/json) |
| iniconfig | 2.3.0 | MIT | [Version metadata](https://pypi.org/pypi/iniconfig/2.3.0/json) |
| jinja2 | 3.1.6 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/jinja2/3.1.6/json) |
| joblib | 1.6.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/joblib/1.6.0/json) |
| kiwisolver | 1.5.1 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/kiwisolver/1.5.1/json) |
| librt | 0.15.0 | MIT | [Version metadata](https://pypi.org/pypi/librt/0.15.0/json) |
| markupsafe | 3.0.3 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/markupsafe/3.0.3/json) |
| matplotlib | 3.11.1 | Matplotlib license (PSF-based) and bundled notices | [Version metadata](https://pypi.org/pypi/matplotlib/3.11.1/json) |
| mpmath | 1.3.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/mpmath/1.3.0/json) |
| mypy | 1.20.2 | MIT | [Version metadata](https://pypi.org/pypi/mypy/1.20.2/json) |
| mypy-extensions | 1.1.0 | MIT | [Version metadata](https://pypi.org/pypi/mypy-extensions/1.1.0/json) |
| narwhals | 2.25.0 | MIT | [Version metadata](https://pypi.org/pypi/narwhals/2.25.0/json) |
| networkx | 3.6.1 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/networkx/3.6.1/json) |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [Version metadata](https://pypi.org/pypi/numpy/2.4.6/json) |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [Version metadata](https://pypi.org/pypi/numpy/2.5.3/json) |
| nvidia-cublas | 13.1.1.3 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cublas/13.1.1.3/json) |
| nvidia-cuda-cupti | 13.0.85 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cuda-cupti/13.0.85/json) |
| nvidia-cuda-nvrtc | 13.0.88 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cuda-nvrtc/13.0.88/json) |
| nvidia-cuda-runtime | 13.0.96 | NVIDIA CUDA Toolkit license and bundled notices | [Version metadata](https://pypi.org/pypi/nvidia-cuda-runtime/13.0.96/json) |
| nvidia-cudnn-cu13 | 9.24.0.43 | NVIDIA cuDNN license | [Version metadata](https://pypi.org/pypi/nvidia-cudnn-cu13/9.24.0.43/json) |
| nvidia-cufft | 12.0.0.61 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cufft/12.0.0.61/json) |
| nvidia-cufile | 1.15.1.6 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cufile/1.15.1.6/json) |
| nvidia-curand | 10.4.0.35 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-curand/10.4.0.35/json) |
| nvidia-cusolver | 12.0.4.66 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cusolver/12.0.4.66/json) |
| nvidia-cusparse | 12.6.3.3 | LicenseRef-NVIDIA-Proprietary | [Version metadata](https://pypi.org/pypi/nvidia-cusparse/12.6.3.3/json) |
| nvidia-cusparselt-cu13 | 0.8.1 | NVIDIA proprietary terms | [Version metadata](https://pypi.org/pypi/nvidia-cusparselt-cu13/0.8.1/json) |
| nvidia-nccl-cu13 | 2.30.7 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/nvidia-nccl-cu13/2.30.7/json) |
| nvidia-nvjitlink | 13.3.33 | NVIDIA CUDA Toolkit license and bundled notices | [Version metadata](https://pypi.org/pypi/nvidia-nvjitlink/13.3.33/json) |
| nvidia-nvshmem-cu13 | 3.4.5 | NVIDIA CUDA Toolkit license and bundled notices | [Version metadata](https://pypi.org/pypi/nvidia-nvshmem-cu13/3.4.5/json) |
| nvidia-nvtx | 13.0.85 | Apache-2.0 | [Version metadata](https://pypi.org/pypi/nvidia-nvtx/13.0.85/json) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [Version metadata](https://pypi.org/pypi/packaging/26.3/json) |
| pandas | 3.0.5 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/pandas/3.0.5/json) |
| pathspec | 1.1.1 | MPL-2.0 | [Version metadata](https://pypi.org/pypi/pathspec/1.1.1/json) |
| pillow | 12.3.0 | MIT-CMU | [Version metadata](https://pypi.org/pypi/pillow/12.3.0/json) |
| pluggy | 1.6.0 | MIT | [Version metadata](https://pypi.org/pypi/pluggy/1.6.0/json) |
| pygments | 2.21.0 | BSD-2-Clause | [Version metadata](https://pypi.org/pypi/pygments/2.21.0/json) |
| pyparsing | 3.3.2 | MIT | [Version metadata](https://pypi.org/pypi/pyparsing/3.3.2/json) |
| pyproject-hooks | 1.2.0 | MIT | [Version metadata](https://pypi.org/pypi/pyproject-hooks/1.2.0/json) |
| pytest | 9.1.1 | MIT | [Version metadata](https://pypi.org/pypi/pytest/9.1.1/json) |
| python-dateutil | 2.9.0.post0 | Apache-2.0 OR BSD-3-Clause | [Version metadata](https://pypi.org/pypi/python-dateutil/2.9.0.post0/json) |
| ruff | 0.16.6 | MIT | [Version metadata](https://pypi.org/pypi/ruff/0.16.6/json) |
| scikit-learn | 1.9.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/scikit-learn/1.9.0/json) |
| scipy | 1.17.1 | BSD-3-Clause and bundled notices | [Version metadata](https://pypi.org/pypi/scipy/1.17.1/json) |
| scipy | 1.18.1 | BSD-3-Clause and bundled notices | [Version metadata](https://pypi.org/pypi/scipy/1.18.1/json) |
| setuptools | 83.0.0 | MIT | [Version metadata](https://pypi.org/pypi/setuptools/83.0.0/json) |
| six | 1.17.0 | MIT | [Version metadata](https://pypi.org/pypi/six/1.17.0/json) |
| sympy | 1.14.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/sympy/1.14.0/json) |
| threadpoolctl | 3.6.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/threadpoolctl/3.6.0/json) |
| torch | 2.14.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | [Version metadata](https://pypi.org/pypi/torch/2.14.0/json) |
| torchvision | 0.29.0 | BSD-3-Clause | [Version metadata](https://pypi.org/pypi/torchvision/0.29.0/json) |
| triton | 3.8.0 | MIT | [Version metadata](https://pypi.org/pypi/triton/3.8.0/json) |
| typing-extensions | 4.16.0 | PSF-2.0 | [Version metadata](https://pypi.org/pypi/typing-extensions/4.16.0/json) |
| tzdata | 2026.3 | Apache-2.0 | [Version metadata](https://pypi.org/pypi/tzdata/2026.3/json) |
| wheel | 0.48.0 | MIT | [Version metadata](https://pypi.org/pypi/wheel/0.48.0/json) |

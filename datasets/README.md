# Datasets

Training data for the generative layout engine (Phase 08) is **not committed** (large + licensed).
This folder holds fetch scripts and documentation only.

## RPLAN
- Source: http://staff.ustc.edu.cn/~fuxm/projects/DeepLayout/index.html
- Used to train/fine-tune the layout model (Graph2Plan / House-GAN++ / HouseDiffusion lineage).
- Review and comply with the dataset's license/terms before use.

A `fetch.py` / `prepare.py` pipeline is added in Phase 08 to download and convert raw data into the
project's `ProgramGraph` + `Boundary` + `Plan` training pairs.

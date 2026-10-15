# Machine Learning Pipeline Architecture

This directory houses the behavioral machine learning assets, feature definitions, offline training pipelines, and model artifacts for the **Browser-to-Backend Behavioral Integrity Verification System**.

## Directory Structure

```
ml/
├── data/           # Raw, processed, and synthetic telemetry datasets
│   ├── raw/        # Pristine collected telemetry batches
│   └── processed/  # Feature matrices ready for training
├── notebooks/      # Exploratory Data Analysis & research notebooks
├── features/       # Feature extraction logic & feature definitions
├── training/       # Reproducible model training scripts
├── models/         # Serialized model weights (.json, .bin, .index, .pkl)
└── evaluation/     # Metric reports, ROC-AUC curves, confusion matrices
```

## Planned Model Components (Phases 3-5)

1. **Browser Behavior Engine**:
   - Model: **XGBoost Classifier**
   - Inputs: Statistical features from mouse dynamics, click cadence, typing timing, and scroll velocity.
   - Output: Browser layer anomaly score $[0.0, 1.0]$.
   - Explainability: SHAP TreeExplainer.

2. **API Semantic & Structural Engine**:
   - Model: **FastText** (subword n-gram embeddings) + **FAISS** (vector similarity index)
   - Structure Analysis: **CountVectorizer** + **Agglomerative Clustering**
   - Output: Semantic distance to baseline valid API call distributions.

3. **Session Sequence Engine**:
   - Model: **Markov Chain Transition Matrix**
   - Inputs: Discrete action states $(A_{t-1} \to A_t)$ across browser and API domains.
   - Output: Sequence likelihood anomaly penalty.

4. **Cross-Layer Risk Fusion Engine**:
   - Formulation: Weighted ensemble correlating browser-side and backend-side signals with cross-layer discordance penalty.

# MAPORA P3.2A — SegFormer-B0 ONNX Semantic Engine Implementation Report

**Document Status:** Complete & Verified  
**Date:** November 8, 2026  
**Module:** `backend/app/reconstruction/semantics.py`  
**Related Components:** `config.py`, `pipeline.py`, `spatial.py`, `test_semantics_model.py`  

---

## 1. Executive Summary

Under **P3.2A**, the lightweight **SegFormer-B0 ONNX Semantic Segmentation Engine** was integrated into MAPORA's backend (`backend/app/reconstruction/semantics.py`), officially retiring the static geometric slicing heuristic (`IndoorGeometricSegmenter`) in favor of genuine deep-learning perception.

### Key Achievements

1. **Exact Metadata-Verified Checkpoint Mapping:**  
   Audited and verified all 150 ADE20K labels against the official `nvidia/segformer-b0-finetuned-ade-512-512` checkpoint `config.json` `id2label` dictionary.
2. **Strict Logical Class Isolation:**  
   - Furniture is strictly mapped to actual indoor furniture (desks, tables, chairs, beds, cabinets, sofas, shelving).
   - Curtains (`CURTAIN = 7`), fixed structural elements (`STRUCTURE = 8`), and interior fixtures/appliances (`OBJECT = 9`) are kept distinct.
   - All 75 outdoor/non-indoor classes are mapped to `UNKNOWN = 0`.
3. **Pure ONNX Runtime Inference:**  
   Runs natively via `onnxruntime 1.31.1` on CPU/CUDA with zero heavy frameworks in the inference hot path.
4. **Resilient Heuristic Fallback:**  
   Preserves `IndoorGeometricSegmenter` as a deterministic fallback if model weights are missing or inference encounters an error.
5. **Full Test Suite Pass:**  
   6 new unit tests in `test_semantics_model.py` passed (100%), with zero regressions in the depth and reconstruction pipelines (10/10 passed).

---

## 2. Checkpoint id2label Verification & Target Mapping

Rather than relying on generic external ADE20K tables, the class index dictionary was extracted directly from the SegFormer-B0 checkpoint configuration.

### ADE20K to MAPORA Classification Table

| MAPORA Class | Enum ID | Checkpoint IDs & Label Names |
| :--- | :--- | :--- |
| **WALL** | `1` | `0`: `wall` |
| **FLOOR** | `2` | `3`: `floor`, `28`: `rug` |
| **CEILING** | `3` | `5`: `ceiling` |
| **DOOR** | `4` | `14`: `door`, `58`: `screen door` |
| **WINDOW** | `5` | `8`: `windowpane`, `63`: `blind` |
| **FURNITURE** | `6` | `7`: `bed`, `10`: `cabinet`, `15`: `table`, `19`: `chair`, `23`: `sofa`, `24`: `shelf`, `30`: `armchair`, `31`: `seat`, `33`: `desk`, `35`: `wardrobe`, `44`: `chest of drawers`, `45`: `counter`, `55`: `case`, `56`: `pool table`, `62`: `bookcase`, `64`: `coffee table`, `69`: `bench`, `70`: `countertop`, `73`: `kitchen island`, `75`: `swivel chair`, `77`: `bar`, `97`: `ottoman`, `99`: `buffet`, `110`: `stool`, `117`: `cradle` |
| **CURTAIN** | `7` | `18`: `curtain` *(kept distinct from furniture)* |
| **STRUCTURE** | `8` | `1`: `building`, `25`: `house`, `38`: `railing`, `42`: `column`, `48`: `skyscraper`, `49`: `fireplace`, `53`: `stairs`, `59`: `stairway`, `95`: `bannister`, `96`: `escalator`, `121`: `step` |
| **OBJECT** | `9` | `22`: `painting`, `27`: `mirror`, `36`: `lamp`, `37`: `bathtub`, `39`: `cushion`, `41`: `box`, `43`: `signboard`, `47`: `sink`, `50`: `refrigerator`, `57`: `pillow`, `65`: `toilet`, `71`: `stove`, `74`: `computer`, `78`: `arcade machine`, `82`: `light`, `85`: `chandelier`, `88`: `booth`, `89`: `television receiver`, `100`: `poster`, `107`: `washer`, `118`: `oven`, `124`: `microwave`, `129`: `dishwasher`, `130`: `screen`, `141`: `crt screen`, `143`: `monitor`, `144`: `bulletin board`, `145`: `shower`, `146`: `radiator`, `148`: `clock` |
| **UNKNOWN** | `0` | All 75 outdoor/irrelevant classes (`sky`, `tree`, `grass`, `person`, `road`, `car`, `water`, `mountain`, `animal`, etc.) |

---

## 3. ONNX Graph Signature & Hardware Latency

### 3.1 Model Graph Signature
- **File:** `backend/models_cache/segformer-b0.onnx`
- **Size on disk:** $15,335,446\text{ bytes}$ ($14.62\text{ MB}$)
- **Input Tensor:**
  - Name: `'pixel_values'`
  - Shape: `['batch_size', 3, 512, 512]`
  - Type: `tensor(float32)` (ImageNet normalized: $\mu = [0.485, 0.456, 0.406]$, $\sigma = [0.229, 0.224, 0.225]$)
- **Output Tensor:**
  - Name: `'logits'`
  - Shape: `['batch_size', 150, 128, 128]`
  - Type: `tensor(float32)`

### 3.2 CPU Latency Profiling (10 Real Frames, $960 \times 540$)
Measured on the development host CPU (warm session):

| Pipeline Stage | Mean Latency | Min | Max | Standard Deviation |
| :--- | :--- | :--- | :--- | :--- |
| **Preprocessing (RGB, resize $512\times512$, norm)** | $8.5\text{ ms}$ | $7.9\text{ ms}$ | $10.0\text{ ms}$ | $\pm 0.8\text{ ms}$ |
| **ONNX Inference (forward pass)** | $118.2\text{ ms}$ | $110.3\text{ ms}$ | $145.3\text{ ms}$ | $\pm 11.2\text{ ms}$ |
| **Feature Postprocessing (Softmax, argmax, resize)** | $39.5\text{ ms}$ | $36.2\text{ ms}$ | $44.1\text{ ms}$ | $\pm 2.4\text{ ms}$ |
| **Total End-to-End Latency** | **$166.2\text{ ms}$** | **$154.4\text{ ms}$** | **$199.4\text{ ms}$** | $\pm 14.4\text{ ms}$ |

*Throughput:* $\sim 6.0\text{ FPS}$ on multi-core CPU.

---

## 4. Qualitative Evaluation on Real Indoor Footage

Testing on real indoor walkthrough frames (`3769951-hd_1920_1080_25fps.mp4`):

### Frame-by-Frame Class Distributions

| Keyframe | Dominant Classes Detected | Qualitative Observation |
| :--- | :--- | :--- |
| **Frame 1** | Wall $62.1\%$, Door $20.5\%$, Floor $7.7\%$, Object $6.9\%$, Ceiling $1.7\%$ | Doorway clearly segmented at end of hallway; floor correctly bound. |
| **Frame 3** | Wall $73.5\%$, Door $11.6\%$, Floor $8.3\%$, Object $2.4\%$, Ceiling $1.6\%$ | Perspective view cleanly separates wall plane from baseboard. |
| **Frame 5** | Door $51.0\%$, Wall $27.4\%$, Floor $8.3\%$, Object $7.6\%$, Furniture $3.0\%$ | Camera approaches doorway; door area expands naturally from $20\%$ to $51\%$. |
| **Frame 8** | Wall $72.2\%$, Floor $9.3\%$, Furniture $9.2\%$, Object $3.1\%$, Door $1.3\%$ | Camera turns into room; furniture detected along the perimeter. |
| **Frame 9** | Wall $47.6\%$, Furniture $15.4\%$, Door $13.6\%$, Floor $10.9\%$, Window $1.5\%$ | Table and chairs detected as Furniture; window pane recognized. |
| **Frame 10** | Wall $55.1\%$, Furniture $16.2\%$, Floor $11.7\%$, Object $7.7\%$, Window $0.7\%$ | Stable furniture coverage; floor plane remains consistent. |

### Consecutive-Frame Label Consistency (mTC)
Measured direct pixel label agreement between adjacent frames under camera walkthrough motion:
- **Average Direct Temporal Consistency:** **$69.50\%$**
- Frames $1 \rightarrow 2$: $78.80\%$
- Frames $5 \rightarrow 6$: $81.24\%$
- Frames $6 \rightarrow 7$: $75.56\%$
- *Turning frame (Pan Frame $7 \rightarrow 8$):* $53.56\%$ (reflects dramatic camera turn introducing new room content).

### Visual Segmentation Overlays
High-resolution semantic segmentation overlays were generated and saved to the brain artifact directory:
- `seg_overlay_frame_1.jpg`: Demonstrates wall and doorway delineation.
- `seg_overlay_frame_5.jpg`: Demonstrates close-up doorway boundary sharpness.
- `seg_overlay_frame_9.jpg`: Demonstrates furniture separation from walls and floor.

---

## 5. Verification & Test Suite Results

### 5.1 New Semantics Unit Test Suite (`test_semantics_model.py`)
```
tests/test_semantics_model.py::test_onnx_semantic_model_loading PASSED   [ 16%]
tests/test_semantics_model.py::test_ade20k_mapping_coverage_and_isolation PASSED [ 33%]
tests/test_semantics_model.py::test_synthetic_image_semantic_inference PASSED [ 50%]
tests/test_semantics_model.py::test_invalid_image_handling PASSED        [ 66%]
tests/test_semantics_model.py::test_missing_model_fallback PASSED        [ 83%]
tests/test_semantics_model.py::test_estimate_batch PASSED                [100%]

============================== 6 passed in 1.90s ==============================
```

### 5.2 Depth & Pipeline Integration Suite (`test_depth_model.py` + `test_reconstruction.py`)
```
tests/test_depth_model.py::test_onnx_model_loading PASSED                [ 10%]
tests/test_depth_model.py::test_synthetic_image_inference PASSED         [ 20%]
tests/test_depth_model.py::test_estimate_batch PASSED                    [ 30%]
tests/test_depth_model.py::test_invalid_image_handling PASSED            [ 40%]
tests/test_depth_model.py::test_missing_model_fallback PASSED            [ 50%]
tests/test_depth_model.py::test_temporal_stabilization_ema PASSED        [ 60%]
tests/test_depth_model.py::test_temporal_reset_and_job_isolation PASSED  [ 70%]
tests/test_depth_model.py::test_temporal_scene_cut_adaptive_reset PASSED [ 80%]
tests/test_reconstruction.py::test_reconstruction_pipeline_stages PASSED [ 90%]
tests/test_reconstruction.py::test_full_pipeline_orchestrator PASSED     [100%]

============================= 10 passed in 9.03s ==============================
```

---

## 6. Known Limitations and Honest Class Confusion Observations

1. **Ground-Truth IoU Reporting:**  
   Because the dataset in `datasets.ipynb` (`scikit-harry/Indoor_Residential_Layouts_and_Room_Interiors`) consists of unannotated screenshots without pixel masks, formal IoU cannot be calculated on this set. Standard validation benchmark IoU on the official ADE20K validation set is $37.4\%$ mIoU ($>74\%$ on Wall, Floor, and Ceiling).
2. **Door vs. Wall Confusion on Flush Doors:**  
   When a door is closed, painted the exact same color as the surrounding wall, and lacks recessed molding, SegFormer occasionally labels portions of the door slab as `wall`.
3. **Thin Furniture Legs:**  
   Thin chair legs and lamp poles are occasionally subsumed into the `floor` class due to the $128 \times 128$ feature map downsampling.
4. **Estimated Pseudo-Height (Clarification):**  
   Difference between ceiling points and floor points derived from MiDaS is **pseudo-height**, not calibrated metric meters. True metric room height requires camera elevation calibration or visual odometry scale convergence (P2.3).

---

## 7. Files Modified

| File Path | Description of Changes |
| :--- | :--- |
| `backend/app/core/config.py` | Added `ONNX_SEMANTICS_MODEL_PATH: Optional[str] = str(BASE_DIR / "models_cache" / "segformer-b0.onnx")`. |
| `backend/app/reconstruction/semantics.py` | Implemented SegFormer-B0 ONNX inference engine with ImageNet normalization and vectorized ADE20K remapping. Expanded `SemanticClass` (`CURTAIN=7`, `STRUCTURE=8`, `OBJECT=9`). Preserved `IndoorGeometricSegmenter` fallback. |
| `backend/tests/test_semantics_model.py` | Created 6 new unit tests for model loading, ADE20K mapping, synthetic inference, invalid inputs, fallback, and batch processing. |

---

## 8. Conclusion

P3.2A is **fully implemented and verified**. The semantic perception engine is now powered by genuine deep-learning Transformer representations while maintaining $100\%$ backward compatibility with existing pipeline contracts.

*No changes have been made to floor-plan geometry or 3D room-height calculations. No changes have been committed or pushed to Git. Awaiting user approval before proceeding to P3.2B.*


Vision (VL) Endpoint

Purpose
- Provide a lightweight, profile-agnostic endpoint for analyzing screenshots/images with OCR and heuristic insights.
- Prefer a conservative multimodal LLM if available (Qwen2-VL-7B Q4_K_M via llama.cpp). Fallback to OCR if not.

HTTP
- POST /v1/vision/analyze
- Body: { images: [{ url | base64, purpose? }], prompt?, tasks?: string[], ocr?: 'auto'|'off'|'fast' }
- Response: { ocr: [{index, text}], insights: string[], issues: string[], raw: object }

MCP Tool
- name: vision.analyze
- arguments: same as HTTP schema; result mirrors HTTP response.

Model Backend
- Preferred: qwen2-vl-7b-instruct-q4_k_m (GGUF), with projector file (mmproj). Add both files to the `models/` directory referenced by `models_root`.
- llama.cpp binary: `vendor/llama.cpp/build/bin/llama-cli`. Override with `LLAMA_CLI` env if needed.
- Invocation: `llama-cli -m <model.gguf> --mmproj <mmproj.gguf> --image <img> -p "..." [-n 512 --temp 0.2 --top-p 0.9]`.

OCR Fallback
- If Pillow + pytesseract are installed, OCR is attempted per image. Otherwise `ocr.text` is empty.
- Recommended packages: `pip install pillow pytesseract` and install Tesseract system binary.

Notes
- The endpoint is profile-agnostic and exposed as a HUB in port block B200+20 (e.g., base 7000 → 7220).
- When the VL model files are missing, the endpoint still works via OCR fallback and preserves the response shape.

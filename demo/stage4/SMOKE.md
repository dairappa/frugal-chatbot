# Stage 4 (browser page) smoke test (2026-11-19, this PC; the page was Stage 5 in earlier drafts)

## Setup

- **Server:** `python3 serve.py 8765`.
- **Browser:** **headless** Google Chrome with `--enable-unsafe-webgpu --enable-features=Vulkan,WebGPU --use-angle=vulkan --ignore-gpu-blocklist`. These flags force WebGPU on, so this is not what a normal Linux Chrome user gets.
- **Page:** opened with `?autotest=How do I reset my password?`. The page reports each stage to `/log`, which writes `smoke.log`.
- **GPU:** the adapter string was "intel gen-7", an Intel integrated GPU. I did not identify the exact model.

## Runs

| Run | Conditions | Result |
|---|---|---|
| 1 | Model forced to q4f16; the CPU was busy with the local eval | `navigator.gpu` was present, an adapter was found, and **shader-f16 = false**. The weights downloaded in about 2.5 minutes, then the run **failed** with `GPUPipelineError: Invalid ShaderModule`. The q4f16 build needs `shader-f16`. |
| 2 | `?model=...q4f32_1-MLC`; CPU busy with the eval | The model loaded in 93 s (download plus compile). **No answer within about 8 minutes**, so I stopped it. |
| 3 | No `?model`, so the shader-f16 check picks the model; **machine idle** (load average 0.06) | The auto-select chose q4f32 because shader-f16 = false. The model loaded **from the browser cache in 4 s**, so the repeat visit was fast. **No answer within about 9 minutes**, so I stopped it. |

**Machine conditions, confirmed by the author:** the machine is a Mac running Linux with an unstable GPU, and Chrome's hardware acceleration is turned **off** on it. The f16 compile failure and the missing answer are therefore specific to this machine. They are not a limit of WebLLM, and they don't predict what a visitor with GPU acceleration on will see.

**Highest level reached:** the model loads, both from the network and from the cache, but this GPU never generates an answer.

**Not tested:** a modern GPU, a non-headless browser, Safari, Firefox, or a phone.

## Lessons for the article

- "WebGPU is available" doesn't mean the model runs. The default q4f16 builds need `shader-f16`.
- A model can load and still never answer. The fallback needs a timeout, not only a feature check.

## Primary-source facts

These come from the web-llm 0.2.89 `prebuiltAppConfig` and the Hugging Face file listings:

| Model | VRAM | Weights | Notes |
|---|---|---|---|
| Llama-3.2-1B-Instruct-q4f16_1-MLC | 879 MB | 704.5 MB | 4,096-token context window |
| Llama-3.2-3B-Instruct-q4f16_1-MLC | 2,264 MB | 1,816.8 MB | |
| Qwen3-0.6B-q4f16_1-MLC | 1,403 MB | 351.5 MB | Needs more VRAM than the 1B Llama |

The weights come from huggingface.co/mlc-ai/. The WebGPU libraries come from raw.githubusercontent.com/mlc-ai/binary-mlc-llm-libs.

# Instala TRELLIS (Microsoft, imagen -> 3D con textura) en Google Colab con GPU L4 (Colab Pro del usuario).
# Colab trae Python 3.13 y las ruedas compiladas de TRELLIS son de 3.10: se crea un entorno 3.10 aparte con uv.
# Probado 2026-10-16: ~1.5 min. En una celda: %%bash + este contenido, o subirlo y "bash instalar.sh > instalar.log 2>&1".
set -e
cd /content
pip install -q uv
export UV_PYTHON_PREFERENCE=managed UV_PYTHON_DOWNLOADS=automatic
unset UV_SYSTEM_PYTHON PIP_TARGET
uv python install 3.10
[ -x /content/tv/bin/python ] || uv venv -q -p cpython-3.10 /content/tv
P="--python /content/tv/bin/python"
uv pip install $P -q torch==2.5.0 torchvision==0.20.0 xformers==0.0.28.post2 --index-url https://download.pytorch.org/whl/cu124 --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match
uv pip install $P -q easydict rembg onnxruntime-gpu 'numpy<2' plyfile huggingface-hub safetensors trimesh xatlas pyvista pymeshfix igraph spconv-cu120 opencv-python-headless imageio imageio-ffmpeg pillow scipy 'transformers<4.50' open3d git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8
uv pip install $P -q https://huggingface.co/spaces/JeffreyXiang/TRELLIS/resolve/main/wheels/nvdiffrast-0.3.3-cp310-cp310-linux_x86_64.whl https://huggingface.co/spaces/JeffreyXiang/TRELLIS/resolve/main/wheels/diff_gaussian_rasterization-0.0.0-cp310-cp310-linux_x86_64.whl
# xformers 0.0.28 no trae BlockDiagonalMask donde TRELLIS lo busca: la atencion va con flash-attn
uv pip install $P -q https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.0.post2/flash_attn-2.7.0.post2+cu12torch2.5cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
uv pip install $P -q kaolin==0.17.0 -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.0_cu124.html || echo KAOLIN_FALLO
[ -d TRELLIS ] || git clone -q --recursive https://github.com/microsoft/TRELLIS
/content/tv/bin/python -c 'import torch;print(torch.__version__, torch.cuda.get_device_name(0))'
echo INSTALADO

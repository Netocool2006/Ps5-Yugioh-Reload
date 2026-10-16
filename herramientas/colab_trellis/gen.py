# Genera un .glb con textura (2048) y un video de vista previa desde una imagen con fondo transparente (figura.png).
# En Colab, tras instalar.sh: /content/tv/bin/python gen.py figura.png salida.glb
# Kuriboh 2026-10-16 en L4: 30 s de generacion + 147 s de textura, 8.7 MB, 11.7 GB de VRAM.
# En el PC despues: quitar_base.py -> quitar_anillo.py -> quitar_tapa_gris.py 0.06 -> aclarar_textura.py
import os, sys, time
os.environ['SPCONV_ALGO'] = 'native'
os.environ['ATTN_BACKEND'] = 'flash_attn'
os.environ['SPARSE_ATTN_BACKEND'] = 'flash_attn'
sys.path.insert(0, '/content/TRELLIS')
import imageio, torch
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import render_utils, postprocessing_utils

t0 = time.time()
p = TrellisImageTo3DPipeline.from_pretrained('microsoft/TRELLIS-image-large')
p.cuda()
print('modelo cargado %.0fs' % (time.time() - t0))
entrada, salida = sys.argv[1], sys.argv[2]
t0 = time.time()
out = p.run(Image.open(entrada), seed=1, sparse_structure_sampler_params={'steps': 25, 'cfg_strength': 7.5},
            slat_sampler_params={'steps': 25, 'cfg_strength': 3.0})
print('generado %.0fs' % (time.time() - t0))
t0 = time.time()
glb = postprocessing_utils.to_glb(out['gaussian'][0], out['mesh'][0], simplify=0.9, texture_size=2048)
glb.export(salida)
print('glb %.0fs' % (time.time() - t0), os.path.getsize(salida))
v = render_utils.render_video(out['gaussian'][0], num_frames=60)['color']
imageio.mimsave(salida.replace('.glb', '.mp4'), v, fps=20)
print('LISTO', torch.cuda.max_memory_allocated() / 2**30, 'GB')

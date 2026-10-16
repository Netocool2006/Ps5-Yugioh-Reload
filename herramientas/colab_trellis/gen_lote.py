# Genera en lote un .glb con textura (2048) por cada imagen de una carpeta (TRELLIS en Colab, tras instalar.sh).
# Uso: /content/tv/bin/python gen_lote.py <carpeta_entrada> <carpeta_salida>   (salida: <nombre>.glb)
# El modelo se carga una vez; cada monstruo tarda ~3 min en una L4 (30 s generacion + textura).
import glob, os, sys, time
os.environ['SPCONV_ALGO'] = 'native'
os.environ['ATTN_BACKEND'] = 'flash_attn'
os.environ['SPARSE_ATTN_BACKEND'] = 'flash_attn'
sys.path.insert(0, '/content/TRELLIS')
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import postprocessing_utils

entrada, salida = sys.argv[1], sys.argv[2]
os.makedirs(salida, exist_ok=True)
t0 = time.time()
p = TrellisImageTo3DPipeline.from_pretrained('microsoft/TRELLIS-image-large')
p.cuda()
print('modelo cargado %.0fs' % (time.time() - t0), flush=True)
for ruta in sorted(glob.glob(os.path.join(entrada, '*.png'))):
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    destino = os.path.join(salida, nombre + '.glb')
    if os.path.exists(destino):
        continue
    t0 = time.time()
    try:
        out = p.run(Image.open(ruta), seed=1, sparse_structure_sampler_params={'steps': 25, 'cfg_strength': 7.5},
                    slat_sampler_params={'steps': 25, 'cfg_strength': 3.0})
        glb = postprocessing_utils.to_glb(out['gaussian'][0], out['mesh'][0], simplify=0.9, texture_size=2048, verbose=False)
        glb.export(destino)
        print('LISTO %s %.0fs %.1f MB' % (nombre, time.time() - t0, os.path.getsize(destino) / 1e6), flush=True)
    except Exception as e:
        print('FALLO %s: %s' % (nombre, e), flush=True)
print('FIN_LOTE', flush=True)

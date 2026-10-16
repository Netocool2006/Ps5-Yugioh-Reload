# Genera la lista de mazos a inyectar en Data.dat y el mapa numero->mazo
import csv, os

manifest = list(csv.DictReader(open(r"D:\Yugi-Reload\biblioteca\manifest.csv", encoding="utf-8")))
with open(r"D:\Yugi-Reload\launcher\lista_nuevos.txt", "w", encoding="utf-8") as f, \
     open(r"D:\Yugi-Reload\launcher\biblioteca_numeros.csv", "w", newline="", encoding="utf-8") as g:
    w = csv.writer(g)
    w.writerow(["numero", "archivo", "tier", "arquetipo"])
    for i, m in enumerate(manifest):
        num = 100 + i
        f.write("j\\file\\cpu_%03d.ydc;%s\n" % (num, os.path.join(r"D:\Yugi-Reload\biblioteca", m["archivo"])))
        w.writerow([num, m["archivo"], m["tier"], m["arquetipo"]])
print("mazos listados:", len(manifest), "| numeros 100 a", 100 + len(manifest) - 1)

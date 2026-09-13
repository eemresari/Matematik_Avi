"""Matematik Avı yardımcı araçları.

`serve.py` ÜRÜNÜN parçasıdır (matematik.py onu içe aktarır ve EXE'ye girer);
diğerleri geliştirme/üretim araçlarıdır ve pakete girmez.

Bu dosya `tools`'u bir PAKET yapıyor ki Nuitka `import`ları takip edebilsin.
Veri dosyası olarak konsaydı derleyici içindeki import'ları GÖRMEZ ve örneğin
`http.server` pakete hiç girmezdi — EXE açılışta ölürdü.

G8 UYARISI: `--include-package=tools` KULLANMA. Bu klasördeki sanat/üretim
script'leri (gen_heroes, make_art, process_mouse_rig) PIL ve başka ağır
bağımlılıklar çekiyor; hepsi pakete girerdi. Doğrusu:
`--include-module=tools.serve`.
"""

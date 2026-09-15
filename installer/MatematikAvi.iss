; Matematik Avi kurucu tanimi (Inno Setup 6).
;
; ELLE CALISTIRMA: bu dosyayi dogrudan ISCC'ye vermek yerine
;     python build.py --kurucu
; kullan. Surum numarasi ve urun adi surum.py'de tek yerde durur ve oradan
; /D ile gecer; burada elle yazilirsa iki kaynak olur ve ayrisirlar.
;
; PAKETE NE GIRER: build\matematik.dist\* (standalone Nuitka klasoru — EXE +
; yuzlerce DLL/.pyd + web.pak + lisans_web + config.ornek.json). ISCC'den
; ONCE build.kurucu_uret() dist'i tarar: config.json, calib.json,
; aktivasyon.dat, lisanslar.json ya da *.key bulunursa build DURUR.
; tests/test_kurucu.py bunu kilitler.

#ifndef SURUM
  #define SURUM "0.0.0-elle"
#endif
#ifndef URUN
  #define URUN "Matematik Avi"
#endif
#ifndef KURUCU_ADI
  #define KURUCU_ADI "MatematikAvi-Setup-elle-win64"
#endif

#define SIRKET   "Luden Studio"

[Setup]
; KimyaLab/SprayTarih/Aican'dan FARKLI GUID: ayni olsaydi Windows dort oyunu
; ayni program sayar, biri digerini kaldirir/ustune yazardi.
AppId={{05569E5F-1A00-4862-9F20-9B99F1AD17F5}
AppName={#URUN}
AppVersion={#SURUM}
AppVerName={#URUN} {#SURUM}
AppPublisher={#SIRKET}
VersionInfoVersion={#SURUM}
DefaultDirName={autopf}\{#SIRKET}\{#URUN}
DefaultGroupName={#SIRKET}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename={#KURUCU_ADI}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Oyun 64-bit Python'dan derleniyor; 32-bit Windows'ta hic calismaz.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Program Files'a yaziyoruz -> yonetici gerekir. Sergi PC'sinde oyun
; genellikle ortak bir hesaptan acilir, kurulumun tek yerde durmasi destek
; vermeyi kolaylastirir.
PrivilegesRequired=admin
UninstallDisplayName={#URUN} {#SURUM}
UninstallDisplayIcon={app}\{#URUN}.exe

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaustune kisayol olustur"; GroupDescription: "Ek kisayollar:"

[Files]
Source: "..\build\matematik.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#URUN}"; Filename: "{app}\{#URUN}.exe"
Name: "{autodesktop}\{#URUN}"; Filename: "{app}\{#URUN}.exe"; Tasks: masaustu
; Kurulu EXE'de --kalibrasyon'a komut satirisiz erisim: kaynaktan calistirmada
; Kalibrasyon.bat vardi, kurulu EXE'nin yaninda .bat gitmez.
Name: "{group}\{#URUN} - Kalibrasyon"; Filename: "{app}\{#URUN}.exe"; Parameters: "--kalibrasyon"

[Run]
Filename: "{app}\{#URUN}.exe"; Description: "{#URUN} uygulamasini simdi ac"; Flags: nowait postinstall skipifsilent

; KALDIRMA NOTU: kullanicinin kalibrasyonu, config.json'i ve aktivasyonu
; %LOCALAPPDATA%\MatematikAvi altinda durur ve kaldirmada SILINMEZ. Surum
; yukseltmesinde sergiyi yeniden kalibre etmesi gerekmesin diye boyle;
; tamamen temizlemek isteyen o klasoru elle siler (docs/KURULUM.md).

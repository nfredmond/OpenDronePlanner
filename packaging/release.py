"""Collect only expected platform products; keep native launch evidence separate."""
from pathlib import Path
import hashlib,json,shutil,zipfile
root=Path(__file__).resolve().parents[1];out=root/'published';out.mkdir(exist_ok=True)
expected=['OpenDronePlanner-Windows-x64-Setup.exe','OpenDronePlanner-macOS-arm64.dmg','OpenDronePlanner-macOS-x64.dmg','OpenDronePlanner-Linux-x64.deb']
assets=root/'release-assets';checks=[]
for name in expected:
 matches=list(assets.rglob(name));assert len(matches)==1,(name,matches)
 target=out/name;shutil.copy2(matches[0],target)
 with target.open('rb') as f:checks.append(hashlib.file_digest(f,'sha256').hexdigest()+'  '+name)
reports=list(assets.rglob('launch-*.json'));assert len(reports)==4,reports
for report in reports:assert json.loads(report.read_text())['passed'],report
with zipfile.ZipFile(out/'native-launch-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for path in assets.rglob('launch-*'):
  if path.is_file():z.write(path,path.relative_to(assets))
(out/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n')

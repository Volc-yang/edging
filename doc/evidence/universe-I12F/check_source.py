from pathlib import Path
import subprocess,unittest
ROOT=Path(__file__).resolve().parents[3]
BASE='227a7501516a819a92e27d5f0551dd52839c6fe5'
PREFIX='engine_platforms/unreal/EdgeWorldHost/'
AUDIT=PREFIX+'Plugins/EdgeWorldRuntime/Source/EdgeWorldRuntime/'
HOST=PREFIX+'Source/EdgeWorldHost/'
class Guards(unittest.TestCase):
 def test_collector_and_schema_byte_unchanged(self):
  p=AUDIT+'Private/EdgeWorldUniverseAssetAudit.cpp'
  old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT,text=True)
  new=(ROOT/p).read_text()
  self.assertEqual(old.split('namespace UniverseAssetAudit',1)[1].split('bool FEdgeWorldUniverseAssetAudit::Collect',1)[0],new.split('namespace UniverseAssetAudit',1)[1].split('bool FEdgeWorldUniverseAssetAudit::Collect',1)[0])
 def test_default_editor_and_explicit_standalone_guards(self):
  h=(ROOT/(AUDIT+'Public/EdgeWorldUniverseAssetAudit.h')).read_text()
  c=(ROOT/(AUDIT+'Private/EdgeWorldUniverseAssetAudit.cpp')).read_text()
  self.assertIn('EContext Context = EContext::Editor',h)
  self.assertIn('Context == EContext::Editor ? GIsEditor :',c)
  for guard in ['!GIsEditor && IsRunningGame()', '!FPlatformProperties::RequiresCookedData() && !IsRunningCommandlet()', '!UniverseAssetAudit::Identifier(WorldId)', '!IsInGameThread()', '!GEngine || !GEngine->IsInitialized()']:self.assertIn(guard,c)
  self.assertIn('#if WITH_EDITOR',h);self.assertNotIn('GEditor',c)
 def test_host_strict_checks_unchanged_except_context(self):
  p=HOST+'EdgeWorldUniverseGameMode.cpp'
  old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT,text=True)
  new=(ROOT/p).read_text()
  replacement='FEdgeWorldUniverseAssetAudit::Collect(O.WorldId,A,Error,GIsEditor ? FEdgeWorldUniverseAssetAudit::EContext::Editor : FEdgeWorldUniverseAssetAudit::EContext::InstalledEditorStandalone);'
  self.assertEqual(old,new.replace(replacement,'FEdgeWorldUniverseAssetAudit::Collect(O.WorldId,A,Error);'))
 def test_real_native_selector_has_no_authority_or_transport(self):
  c=(ROOT/(HOST+'EdgeWorldUniverseProtocolTest.cpp')).read_text().split('bool FUniverseStandaloneAssetAuditTest::RunTest',1)[1]
  for s in ['default remains editor-only','invalid world rejected before collection','A.bResolved','A.GapCount,0','A.CandidateDigest']:self.assertIn(s,c)
  for s in ['SendJsonLine','SpawnActor','FileHelper','AuthorityRoot']:self.assertNotIn(s,c)
if __name__=='__main__':unittest.main()

"""Static source guards only; does not implement/execute GUID or claim native tests."""
from pathlib import Path
import re
import unittest
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost'

class IdSourceGuards(unittest.TestCase):
    def test_actual_three_generation_sites_share_fixed_factory(self):
        cpp=(SOURCE/'EdgeWorldUniverseGameMode.cpp').read_text()
        self.assertEqual(2,cpp.count('FEdgeWorldUniverseProtocolIds::Make(FEdgeWorldUniverseProtocolIds::EKind::Request)'))
        self.assertEqual(1,cpp.count('FEdgeWorldUniverseProtocolIds::Make(FEdgeWorldUniverseProtocolIds::EKind::Command)'))
        self.assertNotRegex(cpp,r'EGuidFormats::Digits\b')
        self.assertNotIn('FGuid::NewGuid()',cpp)

    def test_default_and_injected_guids_have_one_digitslower_implementation(self):
        header=(SOURCE/'EdgeWorldUniverseGameMode.h').read_text()
        factory=header.split('struct FEdgeWorldUniverseProtocolIds',1)[1].split('enum class EUniverseClientPhase',1)[0]
        self.assertIn('enum class EKind { Request, Command }',factory)
        self.assertIn('FGuid Guid=FGuid::NewGuid()',factory)
        self.assertEqual(1,factory.count('Guid.ToString(EGuidFormats::DigitsLower)'))
        self.assertNotIn('Prefix',factory)

    def test_native_regression_uses_actual_factory_and_strict_boundaries(self):
        test=(SOURCE/'EdgeWorldUniverseProtocolTest.cpp').read_text().split('bool FUniverseProtocolIdsTest::RunTest',1)[1]
        self.assertIn('0xABCDEF12',test)
        self.assertIn('EKind::Request,Known',test);self.assertIn('EKind::Command,Known',test)
        self.assertIn('FEdgeWorldUniverseControlParser::Request(TEXT("prepare")',test)
        self.assertIn('FEdgeWorldUniverseControlParser::BuildPrepare',test)
        self.assertIn('OldRequest',test);self.assertIn('OldCommand',test)
        self.assertNotIn('SendJsonLine',test);self.assertNotIn('SpawnActor',test)
        self.assertIn('EAutomationTestFlags::ClientContext',(SOURCE/'EdgeWorldUniverseProtocolTest.cpp').read_text())

if __name__=='__main__':unittest.main()

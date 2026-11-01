#include "EdgeWorldUniverseAssetAudit.h"
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "EdgeWorldUniverseObservation.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
static bool ExactText(const FString& A, const FString& B)
{
 return A.Len() == B.Len() && (!A.Len() || FMemory::Memcmp(*A, *B, A.Len() * sizeof(TCHAR)) == 0);
}
static bool SaveNew(const FString& Filename, const FString& Text)
{
 TUniquePtr<FArchive> Writer(IFileManager::Get().CreateFileWriter(*Filename, FILEWRITE_NoReplaceExisting));
 if (!Writer) return false;
 FTCHARToUTF8 Bytes(*Text); Writer->Serialize(const_cast<ANSICHAR*>(Bytes.Get()), Bytes.Length());
 return !Writer->IsError() && Writer->Close();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldUniverseAssetAuditTest, "edgeWorld.UniverseAssetAudit.ExportRegistry", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FEdgeWorldUniverseAssetAuditTest::RunTest(const FString& Parameters)
{
 FString Directory = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_ASSET_AUDIT_OUTPUT"));
 FString WorldId = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_ASSET_AUDIT_WORLD"));
 if (!TestTrue(TEXT("explicit existing absolute raw directory"), !Directory.IsEmpty() && !FPaths::IsRelative(Directory) && IFileManager::Get().DirectoryExists(*Directory))) return false;
 FEdgeWorldUniverseAssetAuditResult First, Second; FString Error;
 if (!TestTrue(*(TEXT("collect Registry and byte audit: ") + Error), FEdgeWorldUniverseAssetAudit::Collect(WorldId, First, Error))) return false;
 TestTrue(TEXT("first audit persisted without overwriting"), SaveNew(Directory / TEXT("collection-first.json"), First.AuditJson));
 if (!TestTrue(TEXT("repeat collection"), FEdgeWorldUniverseAssetAudit::Collect(WorldId, Second, Error))) return false;
 TestTrue(TEXT("second audit persisted independently"), SaveNew(Directory / TEXT("collection-second.json"), Second.AuditJson));
 TestEqual(TEXT("repeat closure disposition"), First.bResolved, Second.bResolved);
 TestTrue(TEXT("repeat candidate is byte-identical"), ExactText(First.CandidateJson, Second.CandidateJson));
 TestTrue(TEXT("repeat complete audit is byte-identical"), ExactText(First.AuditJson, Second.AuditJson));
 TSharedPtr<FJsonObject> Audit;
 if (!TestTrue(TEXT("audit JSON valid"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(First.AuditJson), Audit))) return false;
 TestEqual(TEXT("four authored roots"), Audit->GetArrayField(TEXT("seed_uris")).Num(), 4);
 TestEqual(TEXT("exact frozen declared count"), int32(Audit->GetNumberField(TEXT("A_declared"))), 4);
 TestTrue(TEXT("asset count bounded"), First.AssetCount <= 64);
 TestTrue(TEXT("asset bytes bounded"), First.ObservedFileBytes <= 2147483648LL);
 if (First.bResolved)
 {
  TestEqual(TEXT("complete graph has no gaps"), First.GapCount, 0);
  TestTrue(TEXT("all four roots in content closure"), First.AssetCount >= 4);
  TestTrue(TEXT("actual count only after complete verification"), Audit->HasTypedField<EJson::Number>(TEXT("A_actual")));
  TestTrue(TEXT("candidate record persisted separately"), SaveNew(Directory / TEXT("candidate-record.json"), First.CandidateJson));
  FTCHARToUTF8 Raw(*First.CandidateJson); FString Canon, Digest;
  TestTrue(TEXT("public strict consumer validates candidate shape and caps"), FEdgeWorldUniverseObservationParser::CanonicalRecord(MakeArrayView(reinterpret_cast<const uint8*>(Raw.Get()), Raw.Length()), Canon, Digest, Error));
  TestTrue(TEXT("candidate already canonical"), ExactText(Canon, First.CandidateJson));
  TestTrue(TEXT("candidate digest stable"), ExactText(Digest, First.CandidateDigest));
 }
 else
 {
  TestTrue(TEXT("gap cannot publish candidate"), First.CandidateJson.IsEmpty() && First.CandidateDigest.IsEmpty());
  TestTrue(TEXT("gap reason is explicit"), First.GapCount > 0);
  TestTrue(TEXT("actual count stays null on gap"), Audit->HasTypedField<EJson::Null>(TEXT("A_actual")));
  TestTrue(TEXT("candidate stays null on gap"), Audit->HasTypedField<EJson::Null>(TEXT("candidate_manifest")));
 }
 AddInfo(FString::Printf(TEXT("I0A resolved=%d content_nodes=%d native_terminals=%d gaps=%d observed_bytes=%lld; exporter success alone is not closure acceptance"), First.bResolved ? 1 : 0, First.AssetCount, First.NativeTerminalCount, First.GapCount, First.ObservedFileBytes));
 return true;
}
#endif

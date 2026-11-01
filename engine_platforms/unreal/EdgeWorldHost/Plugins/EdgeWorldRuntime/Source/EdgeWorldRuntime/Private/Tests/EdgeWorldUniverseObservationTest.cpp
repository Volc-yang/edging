#include "EdgeWorldUniverseObservation.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
using J=TSharedPtr<FJsonObject>;
static TArray<uint8> Bytes(const FString& S){FTCHARToUTF8 U(*S);TArray<uint8> B;B.Append(reinterpret_cast<const uint8*>(U.Get()),U.Length());return B;}
static FEdgeWorldUniverseContext Context(const J& X)
{
 FEdgeWorldUniverseContext C;C.WorldId=X->GetStringField(TEXT("world_id"));C.AuthorityRoot=X->GetStringField(TEXT("authority_root"));C.TrustAlgorithm=X->GetStringField(TEXT("trust_algorithm"));C.TrustAnchor=X->GetStringField(TEXT("trust_anchor"));C.ArtifactClass=X->GetStringField(TEXT("artifact_class"));C.ExpectedBuild=X->GetStringField(TEXT("expected_build"));C.ExpectedOptions=X->GetStringField(TEXT("expected_options"));return C;
}
static FEdgeWorldUniverseExpectation Expectation(const J& X,const FEdgeWorldUniverseContext& C)
{
 FEdgeWorldUniverseExpectation E;E.Context=C;J H=X->GetObjectField(TEXT("trusted_head"));E.TrustedHead.Context=Context(H);E.TrustedHead.Head=H->GetStringField(TEXT("head"));E.TrustedHead.Domain=H->GetStringField(TEXT("domain"));E.TrustedHead.Version=H->GetStringField(TEXT("version"));E.TrustedHead.Profile=H->GetStringField(TEXT("profile"));E.TrustedHead.StorageState=H->GetStringField(TEXT("storage_state"));E.RequestId=X->GetStringField(TEXT("expected_request_id"));E.Tick=int64(X->GetNumberField(TEXT("tick")));E.Revision=int64(X->GetNumberField(TEXT("revision")));E.Watermark=int64(X->GetNumberField(TEXT("watermark")));E.bFixtureOnly=true;return E;
}
static TSharedPtr<FJsonValue> Load(const FString& Root,const TCHAR* File)
{
 FString Raw;if(!FFileHelper::LoadFileToString(Raw,*(Root/File)))return {};TSharedPtr<FJsonValue> Result;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Result);return Result;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldUniverseObservationTest,"edgeWorld.UniverseObservation.StrictV02",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FEdgeWorldUniverseObservationTest::RunTest(const FString& Parameters)
{
 const FString Root=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_FIXTURES"));
 if(!TestTrue(TEXT("explicit fixture directory"),!Root.IsEmpty()))return false;
 auto Gold=Load(Root,TEXT("golden.json")),Proof=Load(Root,TEXT("proof_vectors.json")),Neg=Load(Root,TEXT("negative.json")),Ctx=Load(Root,TEXT("trust_context.json"));
 if(!TestTrue(TEXT("frozen fixtures loaded"),Gold&&Proof&&Neg&&Ctx))return false;
 auto C=Context(Ctx->AsObject());int32 GoldCount=0,ProofCount=0,NegativeCount=0,ExcludedCount=0;
 for(const auto& X:Gold->AsArray())
 {
  J G=X->AsObject();FString Hex=G->GetStringField(TEXT("canonical_hex"));TArray<uint8> Raw;Raw.SetNum(Hex.Len()/2);HexToBytes(Hex,Raw.GetData());FString Canon,Digest,Error;
  TestTrue(*G->GetStringField(TEXT("id")),FEdgeWorldUniverseObservationParser::CanonicalRecord(Raw,Canon,Digest,Error));
  TestTrue(TEXT("frozen canonical bytes"),Bytes(Canon)==Raw);TestEqual(TEXT("domain separated SHA"),Digest,G->GetStringField(TEXT("sha256")));++GoldCount;
 }
 for(const auto& X:Proof->AsArray())
 {
  J P=X->AsObject();auto E=Expectation(P->GetObjectField(TEXT("expected")),C);auto Raw=Bytes(P->GetStringField(TEXT("raw")));FEdgeWorldUniverseObservation Out;FString Error;
  bool Valid=FEdgeWorldUniverseObservationParser::Verify(Raw,E,Out,Error);TestTrue(*(P->GetStringField(TEXT("name"))+TEXT(": ")+Error),Valid);
  if(Valid)
  {
   TestEqual(TEXT("selected manifest"),Out.Manifest,P->GetStringField(TEXT("selected_manifest")));TestEqual(TEXT("exact watermark"),Out.Watermark,E.Revision);TestEqual(TEXT("two bound bodies"),Out.Bodies.Num(),2);TestTrue(TEXT("renderable selected dependencies retained"),Out.SelectedRecords.Num()>=30);TestEqual(TEXT("trusted storage label"),Out.StorageState,E.TrustedHead.StorageState);
   bool World=false,Sample=false,Transform=false;for(const auto& R:Out.SelectedRecords){World|=R.Kind==TEXT("world_manifest");Sample|=R.Kind==TEXT("physics_sample");Transform|=R.Kind==TEXT("unit_transform");}TestTrue(TEXT("verified world/sample/transform present"),World&&Sample&&Transform);
  }
  if(Valid){TestEqual(TEXT("wire bytes exclude LF"),Out.WireBytes,int64(Raw.Num()));auto WithLf=Raw;WithLf.Add('\n');TestTrue(TEXT("single final LF allowed"),FEdgeWorldUniverseObservationParser::Verify(WithLf,E,Out,Error));TestEqual(TEXT("optional LF does not count"),Out.WireBytes,int64(Raw.Num()));}
  auto Runtime=E;Runtime.bFixtureOnly=false;TestFalse(TEXT("runtime rejects public synthetic context"),FEdgeWorldUniverseObservationParser::Verify(Raw,Runtime,Out,Error));TestTrue(TEXT("failed verification clears DTO"),Out.SelectedRecords.IsEmpty());
  auto Forged=E;Forged.TrustedHead.Head=FString::ChrN(64,TEXT('a'));TestFalse(TEXT("response cannot establish own trust root"),FEdgeWorldUniverseObservationParser::Verify(Raw,Forged,Out,Error));++ProofCount;
 }
 for(const auto& X:Neg->AsArray())
 {
  J N=X->AsObject();FString Op=N->GetStringField(TEXT("operation")),Name=N->GetStringField(TEXT("name")),Error;bool Valid=false;
  if(Op==TEXT("proof")){auto NC=C;if(N->HasField(TEXT("context")))NC=Context(N->GetObjectField(TEXT("context")));auto E=Expectation(N->GetObjectField(TEXT("expected")),NC);FEdgeWorldUniverseObservation Out;Valid=FEdgeWorldUniverseObservationParser::Verify(Bytes(N->GetStringField(TEXT("raw"))),E,Out,Error);TestTrue(TEXT("negative leaves no publishable DTO"),Out.SelectedRecords.IsEmpty());}
  else if(Op==TEXT("parse")){FString Canon,Digest;Valid=FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(N->GetStringField(TEXT("raw"))),Canon,Digest,Error);}
  else{++ExcludedCount;continue;} // Archive MAC/raw/key checks belong to writer recovery, not selective UE verification.
  TestFalse(*Name,Valid);TestTrue(*(Name+TEXT(" classified")),!Error.IsEmpty());++NegativeCount;
 }
 // Independent boundary vectors: exact ties, cancellation, subnormals, signed zero.
 struct FCase{uint64 Before,After;int64 Expected;};
 const FCase Cases[]={
  {0x0000000000000000ULL,0x3fb0000000000000ULL,62},
  {0x0000000000000000ULL,0x3fc8000000000000ULL,188},
  {0x0000000000000000ULL,0xbfb0000000000000ULL,-62},
  {0x0000000000000000ULL,0xbfc8000000000000ULL,-188},
  {0x3ff0000000000000ULL,0x3ff1000000000000ULL,62},
  {0x3ff0000000000000ULL,0x3ff3000000000000ULL,188},
  {0xbff0000000000000ULL,0xbff1000000000000ULL,-62},
  {0x8000000000000000ULL,0x0000000000000000ULL,0},
  {0x0000000000000001ULL,0x0000000000000000ULL,0},
  {0x0000000000000000ULL,0x8000000000000001ULL,0},
  {0x3ff0000000000000ULL,0x3feffbe76c8b4396ULL,0},
  {0x3ff0000000000000ULL,0x3feffbe76c8b4395ULL,-1},
  {0x4022000000000000ULL,0x4024000000000000ULL,1000},
  {0x4024000000000000ULL,0x4022000000000000ULL,-1000}
 };
 for(const FCase& T:Cases){int64 D=1234;TestTrue(TEXT("exact finite influence accepted"),FEdgeWorldUniverseObservationParser::ExactInfluence(T.Before,T.After,D));TestEqual(TEXT("exact half even/cancellation"),D,T.Expected);}
 int64 D;TestFalse(TEXT("influence over bound"),FEdgeWorldUniverseObservationParser::ExactInfluence(0,0x4000000000000000ULL,D));TestFalse(TEXT("nonfinite influence"),FEdgeWorldUniverseObservationParser::ExactInfluence(0,0x7ff0000000000000ULL,D));
 // Decoded-key collisions, invalid UTF8, float/bool coercion, wire framing and extra response fields.
 auto Base=Proof->AsArray()[0]->AsObject();auto E=Expectation(Base->GetObjectField(TEXT("expected")),C);FString Wire=Base->GetStringField(TEXT("raw"));FEdgeWorldUniverseObservation Out;FString Error;
 FString Padded=Wire+FString::ChrN(1048576-Bytes(Wire).Num(),TEXT(' '));TestTrue(TEXT("1MiB payload cap inclusive"),FEdgeWorldUniverseObservationParser::Verify(Bytes(Padded),E,Out,Error));TestTrue(TEXT("1MiB plus optional LF accepted"),FEdgeWorldUniverseObservationParser::Verify(Bytes(Padded+TEXT("\n")),E,Out,Error));TestFalse(TEXT("1MiB plus payload byte rejected"),FEdgeWorldUniverseObservationParser::Verify(Bytes(Padded+TEXT(" ")),E,Out,Error));
 TArray<FString> Bad={Wire+TEXT("{}"),Wire+TEXT("\r\n"),TEXT("\n")+Wire,Wire.Replace(TEXT("\"protocol_version\":1"),TEXT("\"protocol_version\":true")),Wire.Replace(TEXT("\"protocol_version\":1"),TEXT("\"protocol_version\":1.0")),Wire.Replace(TEXT("\"ok\":true"),TEXT("\"ok\":true,\"\\u006fk\":true")),Wire.Replace(TEXT("\"request_id\":"),TEXT("\"extra\":0,\"request_id\":"))};
 for(const FString& B:Bad)TestFalse(TEXT("strict wire boundary"),FEdgeWorldUniverseObservationParser::Verify(Bytes(B),E,Out,Error));
 TArray<uint8> InvalidUtf8=Bytes(Wire);InvalidUtf8.Insert(0xc0,0);TestFalse(TEXT("invalid UTF8 not replaced"),FEdgeWorldUniverseObservationParser::Verify(InvalidUtf8,E,Out,Error));
 AddInfo(FString::Printf(TEXT("I9 golden=%d proof=%d applicable_negative=%d writer_only_excluded=%d exact_F=%d"),GoldCount,ProofCount,NegativeCount,ExcludedCount,int32(UE_ARRAY_COUNT(Cases))));
 TestEqual(TEXT("all frozen goldens"),GoldCount,67);TestEqual(TEXT("all selected proof fixtures"),ProofCount,5);TestEqual(TEXT("applicable fixed parse/proof negatives"),NegativeCount,27);TestEqual(TEXT("writer-only archive/blob/key negatives explicitly excluded"),ExcludedCount,30);
 return true;
}
#endif

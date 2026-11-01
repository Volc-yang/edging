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

 // I9S: protocol equality is case-sensitive and counted; FString defaults are unsuitable.
 int32 StrictTextCases = 0;
 auto RejectWire = [&](const TCHAR* Label, const FString& Input)
 {
  TestFalse(Label, FEdgeWorldUniverseObservationParser::Verify(Bytes(Input), E, Out, Error));
  TestTrue(TEXT("strict text failure clears DTO"), Out.SelectedRecords.IsEmpty());
  ++StrictTextCases;
 };
 auto Changed = [&](const TCHAR* From, const TCHAR* To)
 {
  return Wire.Replace(From, To, ESearchCase::CaseSensitive);
 };
 RejectWire(TEXT("operation case is exact"), Changed(TEXT("\"operation\":\"observe\""), TEXT("\"operation\":\"OBSERVE\"")));
 RejectWire(TEXT("domain case is exact"), Changed(TEXT("edgeworld.universe.authority"), TEXT("EDGEWORLD.universe.authority")));
 RejectWire(TEXT("request ID case is exact"), Changed(TEXT("\"request_id\":\"observe-0\""), TEXT("\"request_id\":\"OBSERVE-0\"")));
 RejectWire(TEXT("world case is exact"), Changed(TEXT("composite-demo"), TEXT("COMPOSITE-demo")));
 RejectWire(TEXT("schema key case is exact"), Changed(TEXT("\"ok\":true"), TEXT("\"OK\":true")));
 RejectWire(TEXT("distinct case keys are extra schema keys"), Changed(TEXT("\"ok\":true"), TEXT("\"ok\":true,\"OK\":true")));
 RejectWire(TEXT("NUL inside operation preserved"), Changed(TEXT("\"operation\":\"observe\""), TEXT("\"operation\":\"ob\\u0000serve\"")));
 RejectWire(TEXT("NUL operation suffix cannot alias prefix"), Changed(TEXT("\"operation\":\"observe\""), TEXT("\"operation\":\"observe\\u0000suffix\"")));
 RejectWire(TEXT("NUL key cannot alias decoded schema key"), Changed(TEXT("\"ok\":true"), TEXT("\"o\\u0000k\":true")));
 RejectWire(TEXT("NUL request suffix cannot alias prefix"), Changed(TEXT("\"request_id\":\"observe-0\""), TEXT("\"request_id\":\"observe-0\\u0000suffix\"")));
 auto WrongRoot = E; WrongRoot.TrustedHead.Context.AuthorityRoot = C.AuthorityRoot.Replace(TEXT("edgeworld"), TEXT("EDGEWORLD"), ESearchCase::CaseSensitive);
 TestFalse(TEXT("trusted root spelling is case-sensitive"), FEdgeWorldUniverseObservationParser::Verify(Bytes(Wire), WrongRoot, Out, Error)); ++StrictTextCases;
 auto WrongTrust = E; WrongTrust.TrustedHead.Context.TrustAlgorithm = TEXT("LOCAL-hmac-sha256.v0.2");
 TestFalse(TEXT("trust context spelling is case-sensitive"), FEdgeWorldUniverseObservationParser::Verify(Bytes(Wire), WrongTrust, Out, Error)); ++StrictTextCases;
 auto WrongStorage = E; WrongStorage.TrustedHead.StorageState = TEXT("READY");
 TestFalse(TEXT("trusted storage enum case is exact"), FEdgeWorldUniverseObservationParser::Verify(Bytes(Wire), WrongStorage, Out, Error)); ++StrictTextCases;
 auto NulRoot = E;
 auto& RootChars = NulRoot.Context.AuthorityRoot.GetCharArray(); RootChars.Pop(); RootChars.Add(0); RootChars.Append(TEXT("suffix"), 6); RootChars.Add(0);
 NulRoot.TrustedHead.Context.AuthorityRoot = NulRoot.Context.AuthorityRoot;
 TestFalse(TEXT("counted embedded NUL root rejected"), FEdgeWorldUniverseObservationParser::Verify(Bytes(Wire), NulRoot, Out, Error)); ++StrictTextCases;

 // Generic object keys may differ in case or contain NUL; only exact decoded duplicates collide.
 auto OptionsRecord = [](const FString& Declarations)
 {
  return TEXT("{\"body\":{\"artifact_class\":\"synthetic-contract-only\",\"declarations\":") + Declarations
   + TEXT(",\"exports\":{},\"normalizer\":\"public-model-dump.v0.2\",\"parameter_hash\":\"") + FString::ChrN(64, TEXT('a'))
   + TEXT("\",\"resolution\":\"static-declared\"},\"domain\":\"edgeworld.universe.authority\",\"id\":\"options-text\",\"kind\":\"resolved_options\",\"refs\":{\"build\":\"")
   + FString::ChrN(64, TEXT('b')) + TEXT("\"},\"version\":\"0.2\",\"world_id\":\"composite-demo\"}");
 };
 auto CheckObject = [&](const TCHAR* Label, const FString& Input, const FString& ExpectedObject)
 {
  FString Canon, Digest, CodecError;
  TestTrue(Label, FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(OptionsRecord(Input)), Canon, Digest, CodecError));
  TestTrue(*(FString(Label)+TEXT(" canonical bytes exact including case/NUL/scalar key order")), Bytes(Canon) == Bytes(OptionsRecord(ExpectedObject)));
  ++StrictTextCases;
 };
 CheckObject(TEXT("case-distinct generic keys accepted"), TEXT("{\"a\":2,\"A\":1}"), TEXT("{\"A\":1,\"a\":2}"));
 CheckObject(TEXT("NUL suffix generic keys remain distinct"), TEXT("{\"a\\u0000y\":3,\"a\":1,\"a\\u0000x\":2}"), TEXT("{\"a\":1,\"a\\u0000x\":2,\"a\\u0000y\":3}"));
 CheckObject(TEXT("NUL value preserves both suffix and byte identity"), TEXT("{\"x\":\"a\\u0000b\"}"), TEXT("{\"x\":\"a\\u0000b\"}"));
 CheckObject(TEXT("scalar ordinal U+E000 before U+10000"), TEXT("{\"\\ud800\\udc00\":2,\"\\ue000\":1}"), TEXT("{\"\\ue000\":1,\"\\ud800\\udc00\":2}"));
 CheckObject(TEXT("raw UTF8 nonBMP/scalar keys accepted and ordered"), TEXT("{\"\U00010000\":2,\"\uE000\":1}"), TEXT("{\"\\ue000\":1,\"\\ud800\\udc00\":2}"));
 FString Canon, Digest, CodecError;
 TestFalse(TEXT("escape-equivalent duplicate keys rejected"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(OptionsRecord(TEXT("{\"a\":1,\"\\u0061\":2}"))), Canon, Digest, CodecError)); ++StrictTextCases;
 TestFalse(TEXT("NUL-preserving escape-equivalent duplicate keys rejected"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(OptionsRecord(TEXT("{\"a\\u0000x\":1,\"\\u0061\\u0000x\":2}"))), Canon, Digest, CodecError)); ++StrictTextCases;
 auto ProposalRecord = [](const FString& Output)
 {
  return TEXT("{\"body\":{\"output\":\"") + Output + TEXT("\",\"principal\":\"fixture-principal\"},\"domain\":\"edgeworld.universe.authority\",\"id\":\"proposal-text\",\"kind\":\"proposal\",\"refs\":{},\"version\":\"0.2\",\"world_id\":\"composite-demo\"}");
 };
 FString NonBmp;
 for (int32 I = 0; I < 600; ++I) NonBmp += TEXT("\\ud800\\udc00");
 TestTrue(TEXT("600 nonBMP scalars accepted despite 1200 UTF16 units"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(ProposalRecord(NonBmp)), Canon, Digest, CodecError)); ++StrictTextCases;
 for (int32 I = 600; I < 1024; ++I) NonBmp += TEXT("\\ud800\\udc00");
 TestTrue(TEXT("1024 nonBMP scalars exactly 4096 UTF8 bytes accepted"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(ProposalRecord(NonBmp)), Canon, Digest, CodecError)); ++StrictTextCases;
 TestFalse(TEXT("1025 ASCII scalars hit output cap independently of UTF8 cap"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(ProposalRecord(FString::ChrN(1025, TEXT('a')))), Canon, Digest, CodecError)); ++StrictTextCases;
 TestFalse(TEXT("1025 nonBMP scalars hit UTF8 byte cap"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(ProposalRecord(NonBmp + TEXT("\\ud800\\udc00"))), Canon, Digest, CodecError)); ++StrictTextCases;
 // The frozen config's canonical equality must preserve case too.
 for (const auto& X : Gold->AsArray())
 {
  J G = X->AsObject();
  if (G->GetStringField(TEXT("id")).Equals(TEXT("existence-world"), ESearchCase::CaseSensitive))
  {
   FString Hex = G->GetStringField(TEXT("canonical_hex")); TArray<uint8> Raw; Raw.SetNum(Hex.Len() / 2); HexToBytes(Hex, Raw.GetData()); Raw.Add(0);
   FString ExistenceText = UTF8_TO_TCHAR(reinterpret_cast<const ANSICHAR*>(Raw.GetData()));
   ExistenceText.ReplaceInline(TEXT("\"category\":\"world\""), TEXT("\"category\":\"WORLD\""), ESearchCase::CaseSensitive);
   TestFalse(TEXT("schema enum values cannot fold case"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(ExistenceText), Canon, Digest, CodecError)); ++StrictTextCases;
  }
  if (G->GetStringField(TEXT("kind")).Equals(TEXT("physics_config"), ESearchCase::CaseSensitive))
  {
   FString Hex = G->GetStringField(TEXT("canonical_hex")); TArray<uint8> Raw; Raw.SetNum(Hex.Len() / 2); HexToBytes(Hex, Raw.GetData());
   FString ConfigText;
   // Add an explicit terminator before conversion; Raw itself is an exact counted frozen vector.
   Raw.Add(0); ConfigText = UTF8_TO_TCHAR(reinterpret_cast<const ANSICHAR*>(Raw.GetData()));
   ConfigText.ReplaceInline(TEXT("\"backend\":\"metal\""), TEXT("\"backend\":\"METAL\""), ESearchCase::CaseSensitive);
   TestFalse(TEXT("config canonical equality cannot fold case"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(ConfigText), Canon, Digest, CodecError)); ++StrictTextCases;
  }
 }
 FString KindSuffix = ProposalRecord(TEXT("valid output"));
 KindSuffix.ReplaceInline(TEXT("\"kind\":\"proposal\""), TEXT("\"kind\":\"proposal\\u0000suffix\""), ESearchCase::CaseSensitive);
 TestFalse(TEXT("kind lookup preserves NUL suffix and rejects unknown kind"), FEdgeWorldUniverseObservationParser::CanonicalRecord(Bytes(KindSuffix), Canon, Digest, CodecError)); ++StrictTextCases;
 TestEqual(TEXT("all new strict text cases executed"), StrictTextCases, 28);
 AddInfo(FString::Printf(TEXT("I9S strict_text_cases=%d"), StrictTextCases));
 AddInfo(FString::Printf(TEXT("I9 golden=%d proof=%d applicable_negative=%d writer_only_excluded=%d exact_F=%d"),GoldCount,ProofCount,NegativeCount,ExcludedCount,int32(UE_ARRAY_COUNT(Cases))));
 TestEqual(TEXT("all frozen goldens"),GoldCount,67);TestEqual(TEXT("all selected proof fixtures"),ProofCount,5);TestEqual(TEXT("applicable fixed parse/proof negatives"),NegativeCount,27);TestEqual(TEXT("writer-only archive/blob/key negatives explicitly excluded"),ExcludedCount,30);
 return true;
}
#endif

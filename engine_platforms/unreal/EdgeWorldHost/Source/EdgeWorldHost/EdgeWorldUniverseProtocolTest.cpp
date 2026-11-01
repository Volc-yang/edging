#include "EdgeWorldUniverseGameMode.h"
#include "EdgeWorldUniverseActor.h"
#include "EdgeWorldJsonlClient.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#if PLATFORM_MAC
#include <CommonCrypto/CommonDigest.h>
#include <sys/stat.h>
#endif
#if WITH_DEV_AUTOMATION_TESTS
namespace
{
TArray<uint8> UB(const FString& S){FTCHARToUTF8 U(*S);TArray<uint8> B;B.Append(reinterpret_cast<const uint8*>(U.Get()),U.Length());return B;}
FString UH(const TArray<uint8>& B){
#if PLATFORM_MAC
 uint8 H[CC_SHA256_DIGEST_LENGTH];CC_SHA256(B.GetData(),B.Num(),H);return BytesToHex(H,CC_SHA256_DIGEST_LENGTH).ToLower();
#else
 return {};
#endif
}
FString PinsJson(){return TEXT("{\"allowed_actions\":[\"physics_step\",\"retain_snapshot\"],\"artifact_class\":\"synthetic-contract-only\",\"authority_root\":\"/synthetic/universe\",\"domain\":\"edgeworld.universe.authority\",\"expected_build\":\"")+FString::ChrN(64,'b')+TEXT("\",\"expected_options\":\"")+FString::ChrN(64,'c')+TEXT("\",\"principal\":\"fixture-owner\",\"profile\":\"composite-rigid-support.v0.2\",\"trust_algorithm\":\"local-hmac-sha256.v0.2\",\"trust_anchor\":\"")+FString::ChrN(64,'a')+TEXT("\",\"version\":\"0.2\",\"world_id\":\"synthetic-world\"}");}
FString Json(const TSharedRef<FJsonObject>& X){FString S;FJsonSerializer::Serialize(X,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&S));return S;}
TSharedPtr<FJsonObject> Object(const FString& S){TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),O);return O;}
FString Status(const FString& Pins)
{
 auto H=Object(Pins);H->RemoveField(TEXT("principal"));H->RemoveField(TEXT("allowed_actions"));H->SetStringField(TEXT("head"),FString::ChrN(64,'d'));H->SetStringField(TEXT("storage_state"),TEXT("ready"));
 auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("world_id"),TEXT("synthetic-world"));P->SetStringField(TEXT("head"),FString::ChrN(64,'d'));P->SetNumberField(TEXT("tick"),0);P->SetNumberField(TEXT("revision"),1);P->SetNumberField(TEXT("watermark"),1);P->SetStringField(TEXT("state"),FString::ChrN(64,'e'));P->SetStringField(TEXT("event"),FString::ChrN(64,'f'));P->SetStringField(TEXT("storage_state"),TEXT("ready"));P->SetStringField(TEXT("artifact_class"),TEXT("synthetic-contract-only"));P->SetObjectField(TEXT("head_binding"),H);
 auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("domain"),TEXT("edgeworld.universe.authority"));R->SetStringField(TEXT("version"),TEXT("0.2"));R->SetStringField(TEXT("world_id"),TEXT("synthetic-world"));R->SetStringField(TEXT("operation"),TEXT("status"));R->SetObjectField(TEXT("payload"),P);
 auto E=MakeShared<FJsonObject>();E->SetNumberField(TEXT("protocol_version"),1);E->SetStringField(TEXT("request_id"),TEXT("u-test"));E->SetBoolField(TEXT("ok"),true);E->SetObjectField(TEXT("result"),R);return Json(E);
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniverseProtocolTest,"edgeWorld.UniverseHost.Protocol",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FUniverseProtocolTest::RunTest(const FString& Parameters)
{
 // All control inputs here are explicitly synthetic test context, never runtime evidence.
 FString P=PinsJson(),Error;auto Raw=UB(P);FEdgeWorldUniversePublicPins Pins;
 TestTrue(TEXT("explicit synthetic pins harness"),FEdgeWorldUniverseControlParser::PublicPins(Raw,UH(Raw),Pins,Error,true));
 FEdgeWorldUniversePublicPins Rejected;TestFalse(TEXT("runtime has no fake switch"),FEdgeWorldUniverseControlParser::PublicPins(Raw,UH(Raw),Rejected,Error));
 TestFalse(TEXT("pins LF rejected"),FEdgeWorldUniverseControlParser::PublicPins(UB(P+TEXT("\n")),UH(Raw),Rejected,Error,true));TestFalse(TEXT("pins wrong hash"),FEdgeWorldUniverseControlParser::PublicPins(Raw,FString::ChrN(64,'0'),Rejected,Error,true));
 FEdgeWorldUniverseControlExpectation E;E.Pins=Pins;E.RequestId=TEXT("u-test");E.Operation=TEXT("status");E.bFixtureOnly=true;FEdgeWorldUniverseControl C;FString Wire=Status(P);
 TestTrue(TEXT("owned-channel status accepts same tick different revision"),FEdgeWorldUniverseControlParser::Verify(UB(Wire+TEXT("\n")),E,C,Error));TestEqual(TEXT("independent revision"),C.Revision,int64(1));TestEqual(TEXT("no tick=revision assumption"),C.Tick,int64(0));
 for(const FString& Bad:TArray<FString>{Wire+TEXT("\r\n"),Wire+TEXT("{}"),Wire.Replace(TEXT("\"protocol_version\":1"),TEXT("\"protocol_version\":true")),Wire.Replace(TEXT("\"protocol_version\":1"),TEXT("\"protocol_version\":1.0")),Wire.Replace(TEXT("\"request_id\":\"u-test\""),TEXT("\"request_id\":\"u-other\"")),Wire.Replace(TEXT("\"operation\":\"status\""),TEXT("\"operation\":\"advance\"")),Wire.Replace(TEXT("\"world_id\":\"synthetic-world\""),TEXT("\"world_id\":\"SYNTHETIC-WORLD\"")),Wire.Replace(TEXT("\"ok\":true"),TEXT("\"ok\":true,\"\\u006fk\":true"))})
 {TestFalse(TEXT("strict control frame/identity"),FEdgeWorldUniverseControlParser::Verify(UB(Bad),E,C,Error));TestFalse(TEXT("rejection clears DTO"),C.bSuccess);}
 auto BadUtf8=UB(Wire);BadUtf8.Insert(0xc0,0);TestFalse(TEXT("raw invalid UTF8"),FEdgeWorldUniverseControlParser::Verify(BadUtf8,E,C,Error));
 auto Wrong=E;Wrong.Pins.Context.TrustAnchor=FString::ChrN(64,'1');TestFalse(TEXT("status cannot grant own context"),FEdgeWorldUniverseControlParser::Verify(UB(Wire),Wrong,C,Error));
 FString Fail=TEXT("{\"protocol_version\":1,\"request_id\":\"u-test\",\"ok\":false,\"error\":{\"code\":\"NOT_READY\",\"message\":\"synthetic\",\"commit_status\":\"unknown\"}}");
 TestTrue(TEXT("unknown preserved as failure"),FEdgeWorldUniverseControlParser::Verify(UB(Fail),E,C,Error));TestFalse(TEXT("error not success"),C.bSuccess);TestEqual(TEXT("unknown classification"),C.CommitStatus,FString(TEXT("unknown")));
 FEdgeWorldUniverseSession S;S.Head.Head=TEXT("verified-head");S.Head.StorageState=TEXT("ready");S.Observation.Manifest=S.Head.Head;S.bHasObservation=true;S.bAssetsValidated=true;S.Phase=EUniverseClientPhase::Latest;
 TestTrue(TEXT("ready can write"),S.CanWrite());TestTrue(TEXT("first edge accepted"),S.SpacePressed());TestFalse(TEXT("held input no second action"),S.SpacePressed());S.SpaceReleased();TestTrue(TEXT("new edge"),S.SpacePressed());
 S.FocusLost();S.SpaceReleased();TestFalse(TEXT("focus recovery held key cannot advance"),S.SpacePressed());TestFalse(TEXT("focus recovery blocks retain too"),S.CanWrite());S.ResumeReleased();TestTrue(TEXT("actual release rearms focus"),S.CanWrite());
 S.LastCommandRecords=TEXT("committed exact closure");S.LastCommandDigest=FString::ChrN(64,'d');TestTrue(TEXT("committed retry uses normal write gate"),S.CanRetryLast());S.HeadTick=5;S.HeadRevision=7;TestTrue(TEXT("exact same tick different revision selection"),S.CanSelectExact(5,6,6));TestFalse(TEXT("watermark mismatch"),S.CanSelectExact(5,6,7));TestFalse(TEXT("future selection rejected"),S.CanSelectExact(6,7,7));S.bHistory=true;TestFalse(TEXT("history cannot retry committed write"),S.CanRetryLast());S.bHistory=false;S.ClearPending();TestEqual(TEXT("successful closure retained after pending cleared"),S.LastCommandRecords,FString(TEXT("committed exact closure")));
 S.bHistory=true;S.SpaceReleased();TestFalse(TEXT("history Space rejected"),S.SpacePressed());S.bHistory=false;S.bUnknown=true;TestFalse(TEXT("unknown blocks writes"),S.CanWrite());S.bUnknown=false;S.Head.StorageState=TEXT("unconfirmed_readonly");TestFalse(TEXT("unconfirmed blocks writes"),S.CanWrite());S.Head.StorageState=TEXT("ready");
 auto T=S.Begin(EUniverseClientPhase::AwaitStatus);TestFalse(TEXT("busy blocks writes"),S.CanWrite());auto Old=T;--Old.Epoch;TestFalse(TEXT("late epoch cannot clear busy"),S.Accept(Old,1));TestTrue(TEXT("still busy"),S.bBusy);TestTrue(TEXT("fresh bootstrap generation"),S.Accept(T,1));
 T=S.Begin(EUniverseClientPhase::Advancing);TestFalse(TEXT("new process cannot complete old write"),S.Accept(T,2));S.CommandRecords=TEXT("exact immutable synthetic closure");S.CommandDigest=FString::ChrN(64,'a');S.bUnknown=true;S.Invalidate();TestEqual(TEXT("unknown cached closure survives epoch"),S.CommandRecords,FString(TEXT("exact immutable synthetic closure")));TestTrue(TEXT("unknown remains explicit"),S.bUnknown);TestFalse(TEXT("old callback invalidated"),S.Accept(T,1));
 FEdgeWorldUniverseObservation O;O.OriginCm=FVector3d(10,20,30);O.Scale=100;TestTrue(TEXT("position units/reflection"),AEdgeWorldUniverseActor::Position(O,FVector3d(1,2,3)).Equals(FVector(110,-180,330)));
 TestTrue(TEXT("linear velocity"),AEdgeWorldUniverseActor::LinearVelocity(FVector3d(1,2,3),100).Equals(FVector(100,-200,300)));TestTrue(TEXT("axial angular velocity"),AEdgeWorldUniverseActor::AngularVelocity(FVector3d(1,2,3)).Equals(FVector(-1,2,-3)));
 const double A=FMath::Sqrt(.5);TestTrue(TEXT("quaternion WXYZ reflection"),AEdgeWorldUniverseActor::Quaternion(FVector4d(A,0,0,A)).Equals(FQuat(0,0,-A,A)));
 O.WorldId=Pins.Context.WorldId;O.StorageState=TEXT("ready");O.Config=FString::ChrN(64,'a');O.Binding=FString::ChrN(64,'b');O.Budget=5;FString Payload,Proposal,Intent;
 TestTrue(TEXT("frozen physics prepare"),FEdgeWorldUniverseControlParser::BuildPrepare(Pins,O,TEXT("c-test"),TEXT("physics_step"),TEXT("weak"),Payload,Proposal,Intent,Error));FString First=Payload;
 TestTrue(TEXT("prepare stable IDs/bytes"),FEdgeWorldUniverseControlParser::BuildPrepare(Pins,O,TEXT("c-test"),TEXT("physics_step"),TEXT("weak"),Payload,Proposal,Intent,Error));TestEqual(TEXT("same prepare request"),Payload,First);
 // Synthetic receipt-shaped control packets are checked structurally, never treated as MAC proof.
 auto PP=Object(Proposal),II=Object(Intent);auto HashRecord=[&](const TSharedPtr<FJsonObject>& R){FString Canon,Digest,Why;TestTrue(TEXT("test record canonical hash"),FEdgeWorldUniverseObservationParser::CanonicalRecord(UB(Json(R.ToSharedRef())),Canon,Digest,Why));return Digest;};
 auto AP=Object(Proposal);AP->SetStringField(TEXT("kind"),TEXT("approval"));AP->SetStringField(TEXT("id"),TEXT("approval-c-test"));auto AB=MakeShared<FJsonObject>();AB->SetStringField(TEXT("principal"),Pins.Principal);AB->SetStringField(TEXT("receipt_id"),TEXT("approval-c-test"));AB->SetStringField(TEXT("auth_tag"),FString::ChrN(64,'0'));AB->SetNumberField(TEXT("expires_revision"),0);AP->SetObjectField(TEXT("body"),AB);auto AR=MakeShared<FJsonObject>();AR->SetStringField(TEXT("proposal"),HashRecord(PP));AR->SetStringField(TEXT("intent"),HashRecord(II));AP->SetObjectField(TEXT("refs"),AR);
 auto CM=Object(Proposal);CM->SetStringField(TEXT("kind"),TEXT("command"));CM->SetStringField(TEXT("id"),TEXT("record-c-test"));CM->SetObjectField(TEXT("body"),MakeShared<FJsonObject>());auto CR=MakeShared<FJsonObject>();CR->SetStringField(TEXT("proposal"),HashRecord(PP));CR->SetStringField(TEXT("intent"),HashRecord(II));CR->SetStringField(TEXT("approval"),HashRecord(AP));CM->SetObjectField(TEXT("refs"),CR);FString CD=HashRecord(CM);
 auto PrepareWire=Object(Wire),PR=PrepareWire->GetObjectField(TEXT("result"));PR->SetStringField(TEXT("operation"),TEXT("prepare"));auto PS=MakeShared<FJsonObject>();PS->SetObjectField(TEXT("head_binding"),Object(Wire)->GetObjectField(TEXT("result"))->GetObjectField(TEXT("payload"))->GetObjectField(TEXT("head_binding")));PS->SetArrayField(TEXT("command_records"),{MakeShared<FJsonValueObject>(PP),MakeShared<FJsonValueObject>(II),MakeShared<FJsonValueObject>(AP),MakeShared<FJsonValueObject>(CM)});PS->SetStringField(TEXT("command_digest"),CD);PS->SetField(TEXT("committed_result"),MakeShared<FJsonValueNull>());PR->SetObjectField(TEXT("payload"),PS);
 auto PE=E;PE.Operation=TEXT("prepare");PE.ProposalJson=Proposal;PE.IntentJson=Intent;PE.ApprovalId=TEXT("approval-c-test");PE.CommandRecordId=TEXT("record-c-test");
 TestTrue(TEXT("exact prepared closure accepted"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),PE,C,Error));TestEqual(TEXT("exact command digest retained"),C.CommandDigest,CD);
 AB->SetNumberField(TEXT("expires_revision"),63);TestFalse(TEXT("prepare must match fixed expiry policy"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),PE,C,Error));AB->SetNumberField(TEXT("expires_revision"),0);
 auto Result=Object(Proposal);Result->SetStringField(TEXT("kind"),TEXT("result"));Result->SetStringField(TEXT("id"),TEXT("result-c-test"));auto RB=MakeShared<FJsonObject>();RB->SetStringField(TEXT("command_id"),TEXT("c-test"));RB->SetNumberField(TEXT("tick"),1);RB->SetNumberField(TEXT("revision"),1);RB->SetNumberField(TEXT("watermark"),1);Result->SetObjectField(TEXT("body"),RB);auto RR=MakeShared<FJsonObject>();for(const TCHAR* Key:{TEXT("state"),TEXT("event"),TEXT("checkpoint")})RR->SetStringField(Key,FString::ChrN(64,'a'));RR->SetStringField(TEXT("command"),CD);Result->SetObjectField(TEXT("refs"),RR);
 PR->SetStringField(TEXT("operation"),TEXT("advance"));PS->RemoveField(TEXT("command_records"));PS->RemoveField(TEXT("command_digest"));PS->RemoveField(TEXT("committed_result"));PS->SetObjectField(TEXT("result"),Result);PS->SetStringField(TEXT("manifest"),FString::ChrN(64,'e'));PS->SetStringField(TEXT("commit_status"),TEXT("confirmed"));auto AE=E;AE.Operation=TEXT("advance");AE.CommandDigest=CD;
 TestTrue(TEXT("idempotent result manifest may differ from current binding"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),AE,C,Error));RR->SetStringField(TEXT("command"),FString::ChrN(64,'0'));TestFalse(TEXT("wrong committed command rejected"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),AE,C,Error));
 // The cached prepare result has its own exact watermarks, independent of current HEAD.
 RR->SetStringField(TEXT("command"),CD);RB->SetNumberField(TEXT("tick"),0);PR->SetStringField(TEXT("operation"),TEXT("prepare"));PS->RemoveField(TEXT("manifest"));PS->RemoveField(TEXT("result"));PS->RemoveField(TEXT("commit_status"));PS->SetArrayField(TEXT("command_records"),{MakeShared<FJsonValueObject>(PP),MakeShared<FJsonValueObject>(II),MakeShared<FJsonValueObject>(AP),MakeShared<FJsonValueObject>(CM)});PS->SetStringField(TEXT("command_digest"),CD);PS->SetObjectField(TEXT("committed_result"),Result);
 TestTrue(TEXT("cached result accepts same tick different revision"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),PE,C,Error));RB->SetNumberField(TEXT("watermark"),0);TestFalse(TEXT("cached result rejects mismatched watermark"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),PE,C,Error));RB->SetNumberField(TEXT("watermark"),1);RB->SetNumberField(TEXT("tick"),2);TestFalse(TEXT("cached result rejects tick greater than revision"),FEdgeWorldUniverseControlParser::Verify(UB(Json(PrepareWire.ToSharedRef())),PE,C,Error));
 FEdgeWorldUniverseSession Init;TestFalse(TEXT("readonly existing NOT_READY never auto initializes"),Init.CanInitialize(TEXT("NOT_READY"),false,false));TestTrue(TEXT("explicit registered empty root"),Init.CanInitialize(TEXT("NOT_READY"),true,false));TestTrue(TEXT("explicit uninitialized root"),Init.CanInitialize(TEXT("UNINITIALIZED"),true,false));TestFalse(TEXT("single initialization attempt"),Init.CanInitialize(TEXT("NOT_READY"),true,true));Init.bUnknown=true;TestFalse(TEXT("unknown never initializes"),Init.CanInitialize(TEXT("NOT_READY"),true,false));
 FString Query,Why;TestFalse(TEXT("builder rejects bool selection"),FEdgeWorldUniverseControlParser::Request(TEXT("observe"),TEXT("u-test"),TEXT("{\"domain\":\"edgeworld.universe.authority\",\"version\":\"0.2\",\"world_id\":\"synthetic-world\",\"tick\":true,\"revision\":1,\"watermark\":1}"),Query,Why));
 TestTrue(TEXT("retain prepare"),FEdgeWorldUniverseControlParser::BuildPrepare(Pins,O,TEXT("c-retain"),TEXT("retain_snapshot"),TEXT("weak"),Payload,Proposal,Intent,Error));TestTrue(TEXT("retain zero cost"),Intent.Contains(TEXT("\"budget\":0")));
 O.StorageState=TEXT("unconfirmed_readonly");TestFalse(TEXT("prepare readonly rejected"),FEdgeWorldUniverseControlParser::BuildPrepare(Pins,O,TEXT("c-test"),TEXT("physics_step"),TEXT("weak"),Payload,Proposal,Intent,Error));
 return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniverseTransportTest,"edgeWorld.UniverseHost.TransportRaw",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FUniverseTransportTest::RunTest(const FString& Parameters)
{
 const FString Python=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_TEST_PYTHON"));if(!TestTrue(TEXT("explicit test Python"),!Python.IsEmpty()&&FPaths::FileExists(Python)))return false;
 FString Root=FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("UniverseTransportSynthetic"),FGuid::NewGuid().ToString(EGuidFormats::Digits)));FString Package=Root/TEXT("engine/universe_authority");IFileManager::Get().MakeDirectory(*Package,true);
 FFileHelper::SaveStringToFile(TEXT(""),*(Root/TEXT("engine/__init__.py")));FFileHelper::SaveStringToFile(TEXT(""),*(Package/TEXT("__init__.py")));
 FString Script=TEXT("import sys,pathlib\nassert sys.argv[1]=='--owner-config' and len(sys.argv)==3\nmode=pathlib.Path(sys.argv[2]).read_text()\nfor line in sys.stdin.buffer:\n sys.stderr.buffer.write(b'synthetic stderr\\x00\\xff\\n');sys.stderr.buffer.flush()\n if mode=='crlf':sys.stdout.buffer.write(b'{\\\"synthetic\\\":true}\\r\\n')\n elif mode=='utf8':sys.stdout.buffer.write(b'\\xc0\\n')\n elif mode=='limit':sys.stdout.buffer.write(b'x'*1048578)\n else:sys.stdout.buffer.write(b'{\\\"synthetic\\\":true}\\n')\n sys.stdout.buffer.flush()\n");
 FString Worker=Package/TEXT("worker.py");FFileHelper::SaveStringToFile(Script,*Worker,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
 for(const TCHAR* Mode:{TEXT("crlf"),TEXT("utf8"),TEXT("limit"),TEXT("valid")})
 {
  FString Owner=Root/TEXT("test-owned-mode");FFileHelper::SaveStringToFile(Mode,*Owner,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
  FEdgeWorldWorkerLaunchConfig Config;Config.LaunchMode=EEdgeWorldWorkerLaunchMode::Universe;Config.PythonExecutable=Python;Config.WorkerScript=Worker;Config.OwnerConfigPath=Owner;Config.RequestTimeoutSeconds=3.;
  FString Trace=Root/(FString(TEXT("trace-"))+Mode);IFileManager::Get().MakeDirectory(*Trace,true);
#if PLATFORM_MAC
  FTCHARToUTF8 TracePath(*Trace);chmod(TracePath.Get(),0700);
#endif
  Config.TraceDirectory=Trace;
  FString Existing=Trace/TEXT("exclusive-sentinel.bin");auto Original=UB(TEXT("original synthetic raw"));TestTrue(TEXT("exclusive first raw"),FEdgeWorldProcessTransport::TraceFileExclusive(Existing,Original));TestFalse(TEXT("existing trace file never overwritten"),FEdgeWorldProcessTransport::TraceFileExclusive(Existing,UB(TEXT("replacement"))));TArray<uint8> Preserved;FFileHelper::LoadFileToArray(Preserved,*Existing);TestTrue(TEXT("existing raw unchanged"),Preserved==Original);
  auto Transport=MakeShared<FEdgeWorldProcessTransport,ESPMode::ThreadSafe>(Config);
  struct FDone{FCriticalSection Lock;bool Ready=false;FEdgeWorldResponse Response;};auto Done=MakeShared<FDone,ESPMode::ThreadSafe>();
  Transport->SendJsonLine({TEXT("u-synthetic"),TEXT("status"),TEXT("{}\n")},[Done](FEdgeWorldResponse&& R){FScopeLock L(&Done->Lock);Done->Response=MoveTemp(R);Done->Ready=true;});
  const double End=FPlatformTime::Seconds()+5.;bool Ready=false;while(FPlatformTime::Seconds()<End){{FScopeLock L(&Done->Lock);Ready=Done->Ready;}if(Ready)break;FPlatformProcess::Sleep(.005f);}
  TestTrue(TEXT("raw transport completed"),Ready);if(Ready){FScopeLock L(&Done->Lock);const auto& R=Done->Response;TestTrue(TEXT("owned process identity"),R.ProcessGeneration==1&&R.WorkerPid>0);if(FString(Mode)==TEXT("limit"))TestEqual(TEXT("bounded noLF stream"),R.ErrorCode,FString(TEXT("LIMIT")));else if(FString(Mode)==TEXT("utf8"))TestTrue(TEXT("invalid UTF8 not replaced"),R.RawJsonl.Num()==2&&R.RawJsonl[0]==0xc0);else if(FString(Mode)==TEXT("crlf"))TestTrue(TEXT("CRLF not trimmed"),R.RawJsonl.Num()>2&&R.RawJsonl[R.RawJsonl.Num()-2]=='\r');else TestTrue(TEXT("LF preserved"),!R.RawJsonl.IsEmpty()&&R.RawJsonl.Last()=='\n');}
  Transport->Shutdown();
  TArray<FString> Metadata;IFileManager::Get().FindFiles(Metadata,*(Trace/TEXT("*.json")),true,false);Metadata.Sort();TArray<uint8> Stdout,Stderr;int32 Requests=0;
  for(const FString& Name:Metadata){FString Text;FFileHelper::LoadFileToString(Text,*(Trace/Name));auto M=Object(Text);TArray<uint8> Bytes;FFileHelper::LoadFileToArray(Bytes,*(Trace/M->GetStringField(TEXT("raw_file"))));FString Direction=M->GetStringField(TEXT("direction"));if(Direction==TEXT("stdout-chunk"))Stdout.Append(Bytes);if(Direction==TEXT("stderr-chunk"))Stderr.Append(Bytes);if(Direction==TEXT("request")){++Requests;TestTrue(TEXT("request original bytes"),Bytes==UB(TEXT("{}\n")));}TestTrue(TEXT("trace process generation"),M->GetStringField(TEXT("generation"))==TEXT("1"));}
  TestEqual(TEXT("one request, passive recorder"),Requests,1);TArray<uint8> ExpectedStderr=UB(TEXT("synthetic stderr"));ExpectedStderr.Add(0);ExpectedStderr.Add(0xff);ExpectedStderr.Add('\n');TestTrue(TEXT("stderr original bytes preserved separately"),Stderr==ExpectedStderr);
  if(Ready&&FString(Mode)!=TEXT("limit")){FScopeLock L(&Done->Lock);TestTrue(TEXT("response raw chunks exact"),Stdout==Done->Response.RawJsonl);}

 }
 return true;
}
#endif

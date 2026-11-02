#include "EdgeWorldUniverseObservation.h"
#include "Misc/AutomationTest.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "Misc/EngineVersion.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#if PLATFORM_MAC
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#endif

#if WITH_DEV_AUTOMATION_TESTS
namespace UniverseProofReplay
{
using J=TSharedPtr<FJsonObject>;
const TCHAR* Bridge=TEXT("universe-i15-native-replay-result.v1");
bool Keys(const J& X,const TCHAR* Names)
{
 TArray<FString> K;FString(Names).ParseIntoArray(K,TEXT(","),false);
 if(!X||X->Values.Num()!=K.Num())return false;for(const FString& S:K)if(!X->HasField(S))return false;return true;
}
bool Text(const J& X,const TCHAR* K,FString& V){return X&&X->TryGetStringField(K,V);}
bool UInt(const J& X,const TCHAR* K,int64& Out)
{
 double N=0;if(!X||!X->TryGetNumberField(K,N)||!FMath::IsFinite(N)||N<0||N>9007199254740991.||N!=FMath::FloorToDouble(N))return false;Out=int64(N);return true;
}
bool Hex(const FString& S,int32 N){if(S.Len()!=N)return false;for(TCHAR C:S)if(!((C>='0'&&C<='9')||(C>='a'&&C<='f')))return false;return true;}
FString Hash(const TArray<uint8>& B)
{
#if PLATFORM_MAC
 uint8 H[CC_SHA256_DIGEST_LENGTH];CC_SHA256(B.GetData(),B.Num(),H);return BytesToHex(H,CC_SHA256_DIGEST_LENGTH).ToLower();
#else
 return {};
#endif
}
TArray<uint8> Bytes(const FString& S){FTCHARToUTF8 U(*S);TArray<uint8> B;B.Append(reinterpret_cast<const uint8*>(U.Get()),U.Length());return B;}
bool Parent(const FString& Path,int& Fd,FString& Leaf)
{
#if PLATFORM_MAC
 if(Path.IsEmpty()||!Path.StartsWith(TEXT("/"))||Path.EndsWith(TEXT("/"))||Path.Contains(TEXT("//")))return false;
 for(TCHAR C:Path)if(!C)return false;
 TArray<FString> Parts;Path.ParseIntoArray(Parts,TEXT("/"),true);if(Parts.IsEmpty())return false;
 for(const FString& P:Parts)if(P==TEXT(".")||P==TEXT(".."))return false;
 Fd=open("/",O_RDONLY|O_DIRECTORY);if(Fd<0)return false;
 for(int32 I=0;I+1<Parts.Num();++I){FTCHARToUTF8 P(*Parts[I]);int Next=openat(Fd,P.Get(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW);close(Fd);Fd=Next;if(Fd<0)return false;}
 Leaf=Parts.Last();return true;
#else
 return false;
#endif
}
bool Read(const FString& Path,int64 Cap,TArray<uint8>& Out)
{
 Out.Reset();
#if PLATFORM_MAC
 int ParentFd=-1;FString Leaf;if(!Parent(Path,ParentFd,Leaf))return false;FTCHARToUTF8 L(*Leaf);
 int Fd=openat(ParentFd,L.Get(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK);if(Fd<0){close(ParentFd);return false;}
 struct stat A{},B{},C{};bool Good=fstat(Fd,&A)==0&&S_ISREG(A.st_mode)&&A.st_size>=0&&A.st_size<=Cap;
 if(Good){Out.SetNumUninitialized(int32(A.st_size));int64 Pos=0;while(Pos<A.st_size){ssize_t N=read(Fd,Out.GetData()+Pos,A.st_size-Pos);if(N<0&&errno==EINTR)continue;if(N<=0){Good=false;break;}Pos+=N;}}
 Good=Good&&fstat(Fd,&B)==0&&fstatat(ParentFd,L.Get(),&C,AT_SYMLINK_NOFOLLOW)==0&&A.st_dev==B.st_dev&&A.st_dev==C.st_dev&&A.st_ino==B.st_ino&&A.st_ino==C.st_ino&&A.st_size==B.st_size&&A.st_size==C.st_size&&A.st_mtimespec.tv_sec==B.st_mtimespec.tv_sec&&A.st_mtimespec.tv_nsec==B.st_mtimespec.tv_nsec&&A.st_ctimespec.tv_sec==B.st_ctimespec.tv_sec&&A.st_ctimespec.tv_nsec==B.st_ctimespec.tv_nsec;
 close(Fd);close(ParentFd);if(!Good)Out.Reset();return Good;
#else
 return false;
#endif
}
bool Write(const FString& Path,const TArray<uint8>& B)
{
#if PLATFORM_MAC
 int ParentFd=-1;FString Leaf;if(!Parent(Path,ParentFd,Leaf))return false;FTCHARToUTF8 L(*Leaf);
 int Fd=openat(ParentFd,L.Get(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(Fd<0){close(ParentFd);return false;}
 int32 Pos=0;bool Good=true;while(Pos<B.Num()){ssize_t N=write(Fd,B.GetData()+Pos,B.Num()-Pos);if(N<0&&errno==EINTR)continue;if(N<=0){Good=false;break;}Pos+=N;}Good=Good&&fsync(Fd)==0;close(Fd);close(ParentFd);return Good;
#else
 return false;
#endif
}
J Object(const TArray<uint8>& B){FUTF8ToTCHAR U(reinterpret_cast<const ANSICHAR*>(B.GetData()),B.Num());FString S(U.Length(),U.Get());J X;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),X);return X;}
bool Ref(const J& Case,const TCHAR* Name,int64 Cap,TArray<uint8>& Out)
{
 const J* R=nullptr;FString Path,Sha;
 return Case&&Case->TryGetObjectField(Name,R)&&Keys(*R,TEXT("path,sha256"))&&Text(*R,TEXT("path"),Path)&&Text(*R,TEXT("sha256"),Sha)&&Hex(Sha,64)&&Read(Path,Cap,Out)&&Hash(Out)==Sha;
}
FString Json(const J& X){FString S;FJsonSerializer::Serialize(X.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&S));return S;}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniversePublicProofReplayTest,"edgeWorld.UniverseHost.PublicProofReplay",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FUniversePublicProofReplayTest::RunTest(const FString& Parameters)
{
 using namespace UniverseProofReplay;
 // An explicitly selected missing fixture is a failure, never a successful skip.
 if(FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_NATIVE_REPLAY"))!=TEXT("1")){AddError(TEXT("explicit native replay opt-in required"));return false;}
 const FString Path=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_REPLAY_MANIFEST"));
 const FString ExpectedSha=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_REPLAY_MANIFEST_SHA256"));
 const FString Output=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_REPLAY_OUTPUT"));
 TArray<uint8> Raw;if(!Hex(ExpectedSha,64)||!Read(Path,262144,Raw)||Hash(Raw)!=ExpectedSha){AddError(TEXT("explicit public manifest bytes/hash required"));return false;}
 J M=Object(Raw);FString Format,Run,Product,Tool;const TArray<TSharedPtr<FJsonValue>>* Cases=nullptr;
 if(!Keys(M,TEXT("format,run_id,product_source_sha,tool_source_sha,cases"))||!Text(M,TEXT("format"),Format)||Format!=TEXT("universe-i15-native-replay.v1")||!Text(M,TEXT("run_id"),Run)||Run.IsEmpty()||!Text(M,TEXT("product_source_sha"),Product)||!Hex(Product,40)||!Text(M,TEXT("tool_source_sha"),Tool)||!Hex(Tool,40)||!M->TryGetArrayField(TEXT("cases"),Cases)||Cases->Num()<1||Cases->Num()>8){AddError(TEXT("bounded replay manifest schema required"));return false;}
 TSet<FString> Ids,RealIds;int32 RealCount=0,NegativeCount=0;
 for(const auto& V:*Cases)
 {
  J C=V->AsObject();FString Id,Origin;bool Accept=false;
  if(!Keys(C,TEXT("case_id,origin,source_case_id,pins_ref,status_request_ref,status_response_ref,observe_request_ref,observe_response_ref,trace_refs,trace_frame_index,expected,expected_accept"))||!Text(C,TEXT("case_id"),Id)||Id.IsEmpty()||Ids.Contains(Id)||!Text(C,TEXT("origin"),Origin)||!C->TryGetBoolField(TEXT("expected_accept"),Accept)){AddError(TEXT("unique explicit cases required"));return false;}
  Ids.Add(Id);
  if(Origin==TEXT("real-trace")&&Accept&&C->HasTypedField<EJson::Null>(TEXT("source_case_id"))){++RealCount;RealIds.Add(Id);}
  else if(Origin==TEXT("derived-negative")&&!Accept){++NegativeCount;}
  else {AddError(TEXT("case origin/expectation invalid"));return false;}
 }
 if(RealCount<1||RealCount>6||NegativeCount>2){AddError(TEXT("real/negative case count exceeded"));return false;}
 TArray<TSharedPtr<FJsonValue>> Results;bool All=true;
 for(const auto& V:*Cases)
 {
  J C=V->AsObject();FString Id,Origin,Source;Text(C,TEXT("case_id"),Id);Text(C,TEXT("origin"),Origin);
  if(Origin==TEXT("derived-negative")&&(!Text(C,TEXT("source_case_id"),Source)||!RealIds.Contains(Source))){AddError(TEXT("negative must name real source case"));return false;}
  const J* X=nullptr;int64 Tick=0,Revision=0,Watermark=0;FString StatusId,ObserveId;bool Expected=false;C->TryGetBoolField(TEXT("expected_accept"),Expected);
  if(!C->TryGetObjectField(TEXT("expected"),X)||!Keys(*X,TEXT("status_request_id,observe_request_id,tick,revision,watermark"))||!Text(*X,TEXT("status_request_id"),StatusId)||!Text(*X,TEXT("observe_request_id"),ObserveId)||!UInt(*X,TEXT("tick"),Tick)||!UInt(*X,TEXT("revision"),Revision)||!UInt(*X,TEXT("watermark"),Watermark)||Watermark!=Revision){AddError(TEXT("explicit request IDs/selection required"));return false;}
  TArray<uint8> PinsBytes,StatusRequest,StatusResponse,ObserveRequest,ObserveResponse;
  if(!Ref(C,TEXT("pins_ref"),16384,PinsBytes)||!Ref(C,TEXT("status_request_ref"),32768,StatusRequest)||!Ref(C,TEXT("status_response_ref"),1048577,StatusResponse)||!Ref(C,TEXT("observe_request_ref"),32768,ObserveRequest)||!Ref(C,TEXT("observe_response_ref"),1048577,ObserveResponse)){AddError(TEXT("original case input hash/path rejected"));return false;}
  FEdgeWorldUniversePublicPins Pins;FString Error;const J* PinsRef=nullptr;C->TryGetObjectField(TEXT("pins_ref"),PinsRef);FString PinsSha;Text(*PinsRef,TEXT("sha256"),PinsSha);
  if(!FEdgeWorldUniverseControlParser::PublicPins(PinsBytes,PinsSha,Pins,Error,false)){AddError(TEXT("runtime public pins rejected: ")+Error);return false;}
  FString Base=TEXT("{\"domain\":\"edgeworld.universe.authority\",\"version\":\"0.2\",\"world_id\":\"")+Pins.Context.WorldId+TEXT("\"");
  FString StatusLine,ObserveLine;
  if(!FEdgeWorldUniverseControlParser::Request(TEXT("status"),StatusId,Base+TEXT("}"),StatusLine,Error)||Bytes(StatusLine)!=StatusRequest||!FEdgeWorldUniverseControlParser::Request(TEXT("observe"),ObserveId,Base+FString::Printf(TEXT(",\"tick\":%lld,\"revision\":%lld,\"watermark\":%lld}"),(long long)Tick,(long long)Revision,(long long)Watermark),ObserveLine,Error)||Bytes(ObserveLine)!=ObserveRequest){AddError(TEXT("original request does not match independent expectation"));return false;}
  FEdgeWorldUniverseControlExpectation CE;CE.Pins=Pins;CE.RequestId=StatusId;CE.Operation=TEXT("status");FEdgeWorldUniverseControl Status;
  if(!FEdgeWorldUniverseControlParser::Verify(StatusResponse,CE,Status,Error)||!Status.bSuccess||Status.Head.StorageState!=TEXT("ready")){AddError(TEXT("strict original trusted status required: ")+Error);return false;}
  FEdgeWorldUniverseExpectation E;E.Context=Pins.Context;E.TrustedHead=Status.Head;E.RequestId=ObserveId;E.Tick=Tick;E.Revision=Revision;E.Watermark=Watermark;
  FEdgeWorldUniverseObservation O;const bool Accepted=FEdgeWorldUniverseObservationParser::Verify(ObserveResponse,E,O,Error);
  J R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case_id"),Id);R->SetStringField(TEXT("origin"),Origin);R->SetBoolField(TEXT("accepted"),Accepted);R->SetStringField(TEXT("error"),Error);
  J Input=MakeShared<FJsonObject>();Input->SetStringField(TEXT("pins"),Hash(PinsBytes));Input->SetStringField(TEXT("status_request"),Hash(StatusRequest));Input->SetStringField(TEXT("status_response"),Hash(StatusResponse));Input->SetStringField(TEXT("observe_request"),Hash(ObserveRequest));Input->SetStringField(TEXT("observe_response"),Hash(ObserveResponse));R->SetObjectField(TEXT("actual_input_sha256s"),Input);
  R->SetStringField(TEXT("status_request_id"),StatusId);R->SetStringField(TEXT("observe_request_id"),ObserveId);R->SetNumberField(TEXT("tick"),double(Tick));R->SetNumberField(TEXT("revision"),double(Revision));R->SetNumberField(TEXT("watermark"),double(Watermark));
  R->SetStringField(TEXT("manifest"),O.Manifest);R->SetStringField(TEXT("state"),O.State);R->SetStringField(TEXT("event"),O.Event);
  TArray<TSharedPtr<FJsonValue>> Records;for(const auto& Record:O.SelectedRecords){J Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("digest"),Record.Digest);Item->SetStringField(TEXT("kind"),Record.Kind);Item->SetStringField(TEXT("id"),Record.Id);Records.Add(MakeShared<FJsonValueObject>(Item));}R->SetArrayField(TEXT("selected_records"),Records);
  Results.Add(MakeShared<FJsonValueObject>(R));if(Accepted!=Expected){AddError(TEXT("replay expectation mismatch: ")+Id+TEXT(" ")+Error);All=false;}
 }
 J Result=MakeShared<FJsonObject>();Result->SetStringField(TEXT("format"),Bridge);Result->SetStringField(TEXT("bridge_format"),TEXT("strict-public-status-observe.v1"));Result->SetStringField(TEXT("manifest_sha256"),Hash(Raw));Result->SetNumberField(TEXT("host_pid"),FPlatformProcess::GetCurrentProcessId());Result->SetStringField(TEXT("ue_version"),FEngineVersion::Current().ToString());Result->SetNumberField(TEXT("case_count"),Results.Num());Result->SetArrayField(TEXT("cases"),Results);
 if(!Write(Output,Bytes(Json(Result)+TEXT("\n")))){AddError(TEXT("exclusive native result output required"));return false;}
 return All;
}
#endif

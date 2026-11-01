#include "EdgeWorldUniverseObservation.h"
#if PLATFORM_MAC
#include <CommonCrypto/CommonDigest.h>
#endif

namespace EdgeUniverse
{
constexpr int64 MaxInt = 9007199254740991LL;
struct FValue;
using V = TSharedPtr<FValue>;
struct FValue
{
 enum EType { Null, Bool, Int, String, Array, Object } Type = Null;
 bool B = false; int64 I = 0; FString S; TArray<V> A; TMap<FString,V> O;
};
static V Make(FValue::EType Type) { V X = MakeShared<FValue>(); X->Type = Type; return X; }
static bool Is(const V& X, FValue::EType T) { return X && X->Type == T; }
static V Get(const V& X, const TCHAR* Key) { if (!Is(X,FValue::Object)) return {}; const V* P=X->O.Find(Key); return P ? *P : V(); }
static FString Str(const V& X) { return Is(X,FValue::String) ? X->S : FString(); }
static int64 Num(const V& X) { return Is(X,FValue::Int) ? X->I : -MaxInt; }
static V Body(const V& R) { return Get(R,TEXT("body")); }
static V Refs(const V& R) { return Get(R,TEXT("refs")); }
static FString Kind(const V& R) { return Str(Get(R,TEXT("kind"))); }
static bool Eq(const V& A, const V& B);
static int32 Hex(uint32 C) { return C>='0'&&C<='9'?C-'0':C>='a'&&C<='f'?C-'a'+10:C>='A'&&C<='F'?C-'A'+10:-1; }
static bool LowerHex(const FString& S,int32 N) { if(S.Len()!=N)return false; for(TCHAR C:S)if(!(C>='0'&&C<='9')&&!(C>='a'&&C<='f'))return false; return true; }
static bool Id(const FString& S) { if(S.IsEmpty()||S.Len()>64||S[0]<'a'||S[0]>'z')return false; for(TCHAR C:S)if(!(C>='a'&&C<='z')&&!(C>='0'&&C<='9')&&C!='.'&&C!='_'&&C!='-')return false; return true; }
static void Scalar(FString& S,uint32 C) { if(C>0xffff){C-=0x10000;S.AppendChar(TCHAR(0xd800+(C>>10)));S.AppendChar(TCHAR(0xdc00+(C&1023)));}else S.AppendChar(TCHAR(C)); }
static uint32 NextScalar(const FString& S,int32& I) { uint32 C=uint32(S[I++]); if(C>=0xd800&&C<=0xdbff&&I<S.Len())C=0x10000+((C-0xd800)<<10)+(uint32(S[I++])-0xdc00); return C; }
static bool OrdinalLess(const FString& A,const FString& B) {int32 I=0,J=0;while(I<A.Len()&&J<B.Len()){uint32 X=NextScalar(A,I),Y=NextScalar(B,J);if(X!=Y)return X<Y;}return I==A.Len()&&J<B.Len();}

/** Byte parser: no UE JSON numeric coercion or replacement-character UTF-8 decoding. */
class FReader
{
 TArrayView<const uint8> Bytes; int32 P=0; int32 Nodes=0;
public:
 FString Error;
 explicit FReader(TArrayView<const uint8> B):Bytes(B){}
 bool Fail(const TCHAR* E){if(Error.IsEmpty())Error=E;return false;}
 void Ws(){while(P<Bytes.Num()&&(Bytes[P]==' '||Bytes[P]=='\t'||Bytes[P]=='\n'||Bytes[P]=='\r'))++P;}
 bool ReadString(FString& Out)
 {
  if(P>=Bytes.Num()||Bytes[P++]!='"')return Fail(TEXT("JSON"));
  int32 Utf8Bytes=0;
  while(P<Bytes.Num())
  {
   uint32 C=Bytes[P++]; if(C=='"')return true;
   if(C<32)return Fail(TEXT("JSON"));
   if(C=='\\')
   {
    if(P>=Bytes.Num())return Fail(TEXT("JSON")); C=Bytes[P++];
    switch(C){case '"':case '\\':case '/':break;case 'b':C=8;break;case 'f':C=12;break;case 'n':C=10;break;case 'r':C=13;break;case 't':C=9;break;
    case 'u':{
     auto U16=[&](uint32& U){U=0;for(int32 K=0;K<4;++K){if(P>=Bytes.Num()||Hex(Bytes[P])<0)return false;U=(U<<4)|Hex(Bytes[P++]);}return true;};
     if(!U16(C))return Fail(TEXT("UNICODE"));
     if(C>=0xd800&&C<=0xdbff){if(P+2>Bytes.Num()||Bytes[P++]!='\\'||Bytes[P++]!='u')return Fail(TEXT("UNICODE"));uint32 Low;if(!U16(Low)||Low<0xdc00||Low>0xdfff)return Fail(TEXT("UNICODE"));C=0x10000+((C-0xd800)<<10)+(Low-0xdc00);}
     else if(C>=0xdc00&&C<=0xdfff)return Fail(TEXT("UNICODE"));break;}
    default:return Fail(TEXT("JSON"));}
   }
   else if(C>=128)
   {
    int32 More; uint32 Minimum;
    if(C>=0xc2&&C<=0xdf){More=1;Minimum=0x80;C&=31;}else if(C>=0xe0&&C<=0xef){More=2;Minimum=0x800;C&=15;}else if(C>=0xf0&&C<=0xf4){More=3;Minimum=0x10000;C&=7;}else return Fail(TEXT("UTF8"));
    for(int32 K=0;K<More;++K){if(P>=Bytes.Num()||(Bytes[P]&0xc0)!=0x80)return Fail(TEXT("UTF8"));C=(C<<6)|(Bytes[P++]&63);}
    if(C<Minimum||C>0x10ffff||(C>=0xd800&&C<=0xdfff))return Fail(TEXT("UTF8"));
   }
   Utf8Bytes+=C<0x80?1:C<0x800?2:C<0x10000?3:4;
   if(Utf8Bytes>4096)return Fail(TEXT("LIMIT")); Scalar(Out,C);
  }return Fail(TEXT("JSON"));
 }
 V Value(int32 Depth=0)
 {
  if(Depth>40||++Nodes>100000){Fail(TEXT("LIMIT"));return {};}
  Ws();if(P>=Bytes.Num()){Fail(TEXT("JSON"));return {};}
  uint8 C=Bytes[P]; V X;
  if(C=='"'){X=Make(FValue::String);if(!ReadString(X->S))return {};return X;}
  if(C=='{'||C=='[')
  {
   ++P;bool Obj=C=='{';X=Make(Obj?FValue::Object:FValue::Array);Ws();uint8 End=Obj?'}':']';if(P<Bytes.Num()&&Bytes[P]==End){++P;return X;}
   while(P<Bytes.Num())
   {
    FString Key;if(Obj){Ws();if(!ReadString(Key))return {};if(X->O.Contains(Key)){Fail(TEXT("DUPLICATE_KEY"));return {};}Ws();if(P>=Bytes.Num()||Bytes[P++]!=':'){Fail(TEXT("JSON"));return {};}}
    V Child=Value(Depth+1);if(!Child)return {};if(Obj)X->O.Add(Key,Child);else X->A.Add(Child);
    if((Obj&&X->O.Num()>64)||(!Obj&&X->A.Num()>256)){Fail(TEXT("LIMIT"));return {};}
    Ws();if(P<Bytes.Num()&&Bytes[P]==End){++P;return X;}if(P>=Bytes.Num()||Bytes[P++]!=','){Fail(TEXT("JSON"));return {};}
   }Fail(TEXT("JSON"));return {};
  }
  for(const auto& L : {TPair<const char*,int32>("null",0),TPair<const char*,int32>("true",1),TPair<const char*,int32>("false",2)})
  {
   int32 N=FCStringAnsi::Strlen(L.Key);if(P+N<=Bytes.Num()&&FMemory::Memcmp(Bytes.GetData()+P,L.Key,N)==0){P+=N;X=Make(L.Value==0?FValue::Null:FValue::Bool);X->B=L.Value==1;return X;}
  }
  bool Negative=false;if(C=='-'){Negative=true;++P;}
  if(P>=Bytes.Num()||Bytes[P]<'0'||Bytes[P]>'9'){Fail(TEXT("JSON"));return {};}
  int32 Start=P;uint64 N=0;while(P<Bytes.Num()&&Bytes[P]>='0'&&Bytes[P]<='9'){uint32 D=Bytes[P++]-'0';if(N>(uint64(MaxInt)-D)/10){Fail(TEXT("INTEGER"));return {};}N=N*10+D;}
  if(P-Start>1&&Bytes[Start]=='0'){Fail(TEXT("JSON"));return {};}
  if(P<Bytes.Num()&&(Bytes[P]=='.'||Bytes[P]=='e'||Bytes[P]=='E')){Fail(TEXT("INTEGER"));return {};}
  X=Make(FValue::Int);X->I=Negative?-int64(N):int64(N);return X;
 }
 V Parse(bool Wire)
 {
  int32 PayloadBytes=Bytes.Num()-(Wire&&Bytes.Num()>0&&Bytes.Last()=='\n'?1:0);
  if(PayloadBytes>1048576){Fail(TEXT("PROOF_LIMIT"));return {};}
  if(Wire){for(int32 I=0;I<Bytes.Num();++I)if(Bytes[I]=='\r'||(Bytes[I]=='\n'&&I!=Bytes.Num()-1)){Fail(TEXT("WIRE"));return {};}}
  V X=Value();Ws();if(P!=Bytes.Num()){Fail(TEXT("JSON"));return {};}return X;
 }
};
static FString Quote(const FString& S)
{
 FString Out=TEXT("\"");
 for(TCHAR T:S){uint32 C=uint32(T);switch(C){case '"':Out+=TEXT("\\\"");break;case '\\':Out+=TEXT("\\\\");break;case 8:Out+=TEXT("\\b");break;case 9:Out+=TEXT("\\t");break;case 10:Out+=TEXT("\\n");break;case 12:Out+=TEXT("\\f");break;case 13:Out+=TEXT("\\r");break;default:if(C<32||C>=127)Out+=FString::Printf(TEXT("\\u%04x"),C);else Out.AppendChar(T);}}
 return Out+TEXT("\"");
}
static FString Canon(const V& X)
{
 if(!X)return TEXT("<missing>");switch(X->Type){case FValue::Null:return TEXT("null");case FValue::Bool:return X->B?TEXT("true"):TEXT("false");case FValue::Int:return LexToString(X->I);case FValue::String:return Quote(X->S);
 case FValue::Array:{FString S=TEXT("[");for(int32 I=0;I<X->A.Num();++I){if(I)S+=TEXT(",");S+=Canon(X->A[I]);}return S+TEXT("]");}
 case FValue::Object:{TArray<FString> Keys;X->O.GetKeys(Keys);Keys.Sort(OrdinalLess);FString S=TEXT("{");for(int32 I=0;I<Keys.Num();++I){if(I)S+=TEXT(",");S+=Quote(Keys[I])+TEXT(":")+Canon(X->O[Keys[I]]);}return S+TEXT("}");}}
 return {};
}
static bool Eq(const V& A,const V& B){return A&&B&&Canon(A)==Canon(B);}
static FString Sha(const FString& Text,bool Record=false)
{
 FTCHARToUTF8 Utf8(*Text);TArray<uint8> B;
 if(Record){static const ANSICHAR Prefix[]="edgeworld.universe.authority\0v0.2\0";B.Append(reinterpret_cast<const uint8*>(Prefix),sizeof(Prefix)-1);}
 B.Append(reinterpret_cast<const uint8*>(Utf8.Get()),Utf8.Length());
#if PLATFORM_MAC
 // UE5.8 Mac inherits a GenericPlatformMisc SHA256 stub that asserts. Use the
 // installed Apple system API; unsupported platforms fail closed without calling that stub.
 if(uint64(B.Num())>uint64(TNumericLimits<CC_LONG>::Max()))return {};
 uint8 Hash[CC_SHA256_DIGEST_LENGTH];
 if(CC_SHA256(B.GetData(),static_cast<CC_LONG>(B.Num()),Hash)==nullptr)return {};
 return BytesToHex(Hash,CC_SHA256_DIGEST_LENGTH).ToLower();
#else
 return {};
#endif
}
static bool F64(const V& X,double& D,uint64* Bits=nullptr)
{
 if(!Is(X,FValue::Object)||X->O.Num()!=1)return false;FString S=Str(Get(X,TEXT("$f64")));if(!LowerHex(S,16))return false;
 uint64 U=0;for(TCHAR C:S)U=(U<<4)|Hex(C);if(((U>>52)&2047)==2047)return false;
 FMemory::Memcpy(&D,&U,8);if(Bits)*Bits=U;return true;
}
// Fixed unsigned integer with 36 32-bit limbs (1152 bits). Binary64 |position| <=10
// expressed at 2^-1074 occupies <=1078 bits; multiplying by1000 still fits.
struct FBits
{
 uint32 W[36]={};
 static FBits Decode(uint64 U){FBits R;uint64 M=U&0xfffffffffffffULL;int32 E=(U>>52)&2047;if(E)M|=1ULL<<52;int32 Shift=E?E-1:0;for(int32 I=0;I<53;++I)if((M>>I)&1)R.W[(I+Shift)/32]|=uint32(1) << ((I+Shift)%32);return R;}
 bool Bit(int32 I)const{return (W[I/32]>>(I%32))&1;}
 int32 Compare(const FBits& B)const{for(int32 I=35;I>=0;--I)if(W[I]!=B.W[I])return W[I]>B.W[I]?1:-1;return 0;}
 void Add(const FBits& B){uint64 C=0;for(int32 I=0;I<36;++I){uint64 N=uint64(W[I])+B.W[I]+C;W[I]=uint32(N);C=N>>32;}}
 void Sub(const FBits& B){uint64 Borrow=0;for(int32 I=0;I<36;++I){uint64 S=uint64(B.W[I])+Borrow;uint64 A=W[I];W[I]=uint32(A-S);Borrow=A<S;}}
 void Thousand(){uint64 Carry=0;for(int32 I=0;I<36;++I){uint64 N=uint64(W[I])*1000+Carry;W[I]=uint32(N);Carry=N>>32;}}
};
static bool Influence(uint64 Before,uint64 After,int64& Out)
{
 double A,B;FMemory::Memcpy(&A,&Before,8);FMemory::Memcpy(&B,&After,8);
 if(!FMath::IsFinite(A)||!FMath::IsFinite(B)||FMath::Abs(A)>10||FMath::Abs(B)>10)return false;
 FBits X=FBits::Decode(Before),Y=FBits::Decode(After);bool SX=(Before>>63)!=0,SY=(After>>63)!=0;FBits D;bool Neg;
 // after - before, including signed zeros.
 if(SX!=SY){D=Y;D.Add(X);Neg=SY;}else if(Y.Compare(X)>=0){D=Y;D.Sub(X);Neg=SY;}else{D=X;D.Sub(Y);Neg=!SY;}
 D.Thousand();uint64 Q=0;for(int32 I=1074;I<1152;++I)if(D.Bit(I)){if(I-1074>=63)return false;Q|=1ULL<<(I-1074);}
 bool Lower=false;for(int32 I=0;I<1073;++I)Lower|=D.Bit(I);if(D.Bit(1073)&&(Lower||(Q&1)))++Q;
 if(Q>1000)return false;Out=Neg?-int64(Q):int64(Q);return true;
}

// Frozen G-C0.2 allowlist, not loaded from response or an editable runtime file.
static const ANSICHAR SchemaJson[] = R"schema({"archive_profile":"composite-rigid-support.v0.2","body":{"admission":{"auth_tag":"hash","evaluated_revision":"uint","principal":"id","receipt_id":"id"},"approval":{"auth_tag":"hash","expires_revision":"uint","principal":"id","receipt_id":"id"},"asset_manifest":{"dependency_status":"declared-static|runtime-resolved","entries":"assets"},"candidate":{"adapter_kind":"genesis|checkpoint_reuse","influence_mm":"nullable_mm","physics_profile":"genesis-rigid-support.v0.1","revision":"uint","tick":"uint"},"checkpoint_descriptor":{"artifact_class":"class","byte_count":"blob_size","format":"synthetic-static-bytes|genesis-gstraj","genesis_version":"1.4.3","media_type":"media","payload_sha256":"hash"},"command":{},"event":{"event_id":"id"},"existence":{"category":"world|place|physical","existence_id":"id","spirit_record":"not_separately_assigned"},"index":{"command_id":"id","fingerprint":"hash"},"intent":{"action":"physics_step|retain_snapshot","budget":"uint","case_id":"nullable_case","command_id":"id","expected_revision":"uint","principal":"id","random_cursor":"uint","tick_delta":"delta"},"manifest":{"revision":"uint","tick":"uint","watermark":"uint"},"physics_binding":{"bindings":"bindings"},"physics_config":{"config":"i7_config"},"physics_sample":{"artifact_class":"class","bodies":"bodies","contacts":"contacts","frame_id":"genesis-world-si-zup.v0.1","solver_precision":"32"},"physics_snapshot":{"case_id":"initial|weak|strong","physical_step_count":"steps"},"place":{"elevation_cm":"sint","footprint_cm":"polygon","place_id":"id","place_kind":"city|wildland|plain|forest|river_marsh|ocean"},"projection":{"decorations":"decorations","development_cm_per_mm":"f64","development_layout":"abstract-magnified","physical_layout":"versioned-transform","projection_version":"basicshapes-proxy.v0.2"},"proposal":{"output":"output","principal":"id"},"provider_build":{"adapter_source_sha256":"nullable_hash","artifact_class":"class","critical_sources":"sources","dependencies":"dependencies","distribution":"genesis-world","metadata_sha256":"hash","python_abi":"cpython-312","source_file_count":"uint","source_tree_sha256":"hash","version":"1.4.3"},"resolved_options":{"artifact_class":"class","declarations":"json_object","exports":"json_object","normalizer":"public-model-dump.v0.2","parameter_hash":"hash","resolution":"static-declared|runtime-exported"},"result":{"command_id":"id","revision":"uint","tick":"uint","watermark":"uint"},"route":{"place_ids":"ids","polyline_cm":"polyline","route_id":"id"},"state":{"budget":"uint","development_mm":"nullable_mm","random_cursor":"uint","revision":"uint","tick":"uint"},"unit_transform":{"origin_cm":"vec3","scale":"f64","signs":"signs","source_frame":"genesis-world-si-zup.v0.1","target_frame":"ue-world-cm.v0.2","transform_version":"si-to-ue.v0.2"},"watercourse":{"polyline_cm":"polyline","watercourse_id":"id"},"world_manifest":{"artifact_class":"class","extent_cm":"extent","geography_version":"six-place-proxy.v0.2","physics_rule":"rigid-support-influence.v0.1","revision_rule":"technical-retain-snapshot.v0.2","world_seed":"uint"}},"domain":"edgeworld.universe.authority","kind_bytes":{"admission":2048,"approval":2048,"asset_manifest":65536,"candidate":2048,"checkpoint_descriptor":2048,"command":2048,"event":2048,"existence":1024,"index":2048,"intent":2048,"manifest":2048,"physics_binding":4096,"physics_config":16384,"physics_sample":8192,"physics_snapshot":2048,"place":4096,"projection":16384,"proposal":16384,"provider_build":8192,"resolved_options":32768,"result":2048,"route":4096,"state":2048,"unit_transform":2048,"watercourse":4096,"world_manifest":4096},"limits":{"archive_bytes":16777216,"asset_bytes":2147483648,"assets":64,"blob_bytes":8388608,"current_records":288,"decorations":1000,"geometry_points":4096,"opaque_refs":256,"proof_records":96,"record_array":256,"record_bytes":65536,"record_depth":32,"record_keys":64,"records":2048,"retained_blob_bytes":536870912,"retained_roots":64,"string_bytes":4096,"wire_bytes":1048576},"physics_parameters":{"authority_version":"0.2","backend":"metal","cases":[{"case_id":"weak","gravity_m_s2":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"c000000000000000"}]},{"case_id":"strong","gravity_m_s2":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"c0239eb851eb851f"}]}],"dt_s":{"$f64":"3f847ae147ae147b"},"entities":[{"existence_id":"existence-dynamic","fixed":false,"genesis_name":"i7-dynamic","morph":"sphere","physical_id":"body-dynamic","position_m":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"3ff0000000000000"}],"quaternion_wxyz":[{"$f64":"3ff0000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"}],"radius_m":{"$f64":"3fb999999999999a"},"size_m":null},{"existence_id":"existence-support","fixed":true,"genesis_name":"i7-support","morph":"box","physical_id":"body-support","position_m":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"bfb999999999999a"}],"quaternion_wxyz":[{"$f64":"3ff0000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"}],"radius_m":null,"size_m":[{"$f64":"4010000000000000"},{"$f64":"4010000000000000"},{"$f64":"3fc999999999999a"}]}],"frame":"genesis-world-si-zup.v0.1","genesis_version":"1.4.3","horizon_advances":32,"init_gravity_m_s2":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"c000000000000000"}],"limits":{"angular_velocity_abs_rad_s":{"$f64":"4059000000000000"},"checkpoint_bytes_max":8388608,"contact_force_abs_n":{"$f64":"412e848000000000"},"contacts_max":32,"fixed_pose_error_m":{"$f64":"3eb0c6f7a0b5ed8d"},"ground_gap_max_m":{"$f64":"3f847ae147ae147b"},"ground_gap_min_m":{"$f64":"bf747ae147ae147b"},"influence_mm_abs_max":1000,"linear_velocity_abs_m_s":{"$f64":"4059000000000000"},"position_abs_m":{"$f64":"4024000000000000"},"quaternion_norm_sq_error":{"$f64":"3f1a36e2eb1c432d"},"samples_per_candidate":2,"settled_vz_abs_m_s":{"$f64":"3fa999999999999a"}},"material":{"friction":{"$f64":"3fe0000000000000"},"gravity_compensation":{"$f64":"0000000000000000"},"needs_coup":false,"rho_kg_m3":{"$f64":"408f400000000000"}},"physics_profile":"genesis-rigid-support.v0.1","requires_grad":false,"rigid_options":{"constraint_timeconst_s":{"$f64":"3f847ae147ae147b"},"enable_collision":true,"enable_mujoco_compatibility":false,"enable_rolling_friction":false,"enable_self_collision":true,"enable_torsional_friction":false,"iterations":25,"ls_iterations":50,"max_collision_pairs":16,"max_contacts":32,"use_hibernation":false},"seed":7,"solver_precision":"32","steps_per_advance":8,"substeps":1,"viewer":false},"proof_kind_max":{"admission":1,"approval":1,"asset_manifest":1,"candidate":1,"checkpoint_descriptor":2,"command":1,"event":1,"existence":9,"index":1,"intent":1,"manifest":66,"physics_binding":1,"physics_config":1,"physics_sample":2,"physics_snapshot":2,"place":6,"projection":1,"proposal":1,"provider_build":1,"resolved_options":1,"result":1,"route":2,"state":2,"unit_transform":1,"watercourse":1,"world_manifest":1},"proof_wrapper_reserve":65536,"record_prefix_hex":"65646765776f726c642e756e6976657273652e617574686f726974790076302e3200","refs":{"admission":{"candidate":"candidate","command":"command"},"approval":{"intent":"intent","proposal":"proposal"},"asset_manifest":{},"candidate":{"command":"command","prior_state":"state","snapshot":"physics_snapshot"},"checkpoint_descriptor":{"binding":"physics_binding","build":"provider_build","config":"physics_config"},"command":{"approval":"approval","intent":"intent","proposal":"proposal"},"event":{"admission":"admission","prior_event?":"event","state":"state"},"existence":{},"index":{"result":"result"},"intent":{"binding":"physics_binding","config":"physics_config"},"manifest":{"event?":"event","index?":"index","prior_manifest?":"manifest","state":"state"},"physics_binding":{"config":"physics_config","dynamic_exists":"existence","support_exists":"existence"},"physics_config":{"build":"provider_build","options":"resolved_options"},"physics_sample":{"binding":"physics_binding","config":"physics_config"},"physics_snapshot":{"binding":"physics_binding","checkpoint":"checkpoint_descriptor","config":"physics_config","sample":"physics_sample"},"place":{"existence":"existence"},"projection":{"assets":"asset_manifest","transform":"unit_transform"},"proposal":{},"provider_build":{},"resolved_options":{"build":"provider_build"},"result":{"checkpoint":"physics_snapshot","command":"command","event":"event","state":"state"},"route":{"pN":"place"},"state":{"snapshot":"physics_snapshot","world":"world_manifest"},"unit_transform":{},"watercourse":{"marsh":"place","outlet":"place","upstream":"place"},"world_manifest":{"branch_route":"route","city":"place","dynamic_existence":"existence","forest":"place","main_route":"route","ocean":"place","plain":"place","projection":"projection","river_marsh":"place","support_existence":"existence","watercourse":"watercourse","wildland":"place","world_existence":"existence"}},"trust":{"algorithm":"local-hmac-sha256.v0.2","anchor_prefix_hex":"65646765776f726c642e756e6976657273652e74727573742d616e63686f720076302e3200","fixture_key_sha256":"630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd","receipt_prefix_hex":"65646765776f726c642e756e6976657273652e726563656970740076302e3200"},"version":"0.2"})schema";
class FValidator
{
public:
 FString Error; V Schema; TMap<FString,V> Records; TSet<FString> Needed, Membership;
 explicit FValidator(){FReader R(MakeArrayView(reinterpret_cast<const uint8*>(SchemaJson),int32(sizeof(SchemaJson)-1)));Schema=R.Parse(false);Error=R.Error;}
 bool Require(bool B,const TCHAR* E){if(!B&&Error.IsEmpty())Error=E;return B;}
 bool Exact(const V& X,const V& Shape){if(!Require(Is(X,FValue::Object)&&Is(Shape,FValue::Object),TEXT("SCHEMA")))return false;if(!Require(X->O.Num()==Shape->O.Num(),TEXT("SCHEMA")))return false;for(const auto& K:Shape->O)if(!Require(X->O.Contains(K.Key),TEXT("SCHEMA")))return false;return true;}
 bool Keys(const V& X,const TCHAR* CommaKeys){V S=Make(FValue::Object);TArray<FString> A;FString(CommaKeys).ParseIntoArray(A,TEXT(","));for(const FString& K:A)S->O.Add(K,Make(FValue::Null));return Exact(X,S);}
 bool Uint(const V& X){return Require(Is(X,FValue::Int)&&X->I>=0,TEXT("INTEGER"));}
 bool Hash(const V& X){return Require(Is(X,FValue::String)&&LowerHex(X->S,64),TEXT("REFERENCE"));}
 bool Identity(const V& X){return Require(Is(X,FValue::String)&&Id(X->S),TEXT("ID"));}
 bool Tree(const V& X,int32 D=0){if(!Require(X&&D<=32,TEXT("LIMIT")))return false;if(Is(X,FValue::Object)){if(X->O.Contains(TEXT("$f64"))){double F;return Require(F64(X,F),TEXT("F64"));}for(const auto& P:X->O)if(!Tree(P.Value,D+1))return false;}else if(Is(X,FValue::Array))for(const V& C:X->A)if(!Tree(C,D+1))return false;return true;}
 bool Vec(const V& X,int32 N,double Bound){if(!Require(Is(X,FValue::Array)&&X->A.Num()==N,TEXT("PHYSICS_INVALID")))return false;for(const V& C:X->A){double D;if(!Require(F64(C,D)&&FMath::Abs(D)<=Bound,TEXT("PHYSICS_INVALID")))return false;}return true;}
 bool IntVec(const V& X,int32 N){if(!Require(Is(X,FValue::Array)&&X->A.Num()==N,TEXT("GEOGRAPHY")))return false;for(const V& C:X->A)if(!Require(Is(C,FValue::Int),TEXT("INTEGER")))return false;return true;}
 bool Field(const V& X,const FString& S)
 {
  if(S==TEXT("id"))return Identity(X);if(S==TEXT("hash"))return Hash(X);if(S==TEXT("nullable_hash"))return Is(X,FValue::Null)||Hash(X);
  if(S==TEXT("uint"))return Uint(X);if(S==TEXT("sint"))return Require(Is(X,FValue::Int),TEXT("INTEGER"));
  if(S==TEXT("f64")){double D;return Require(F64(X,D),TEXT("F64"));}
  if(S==TEXT("nullable_mm"))return Require(Is(X,FValue::Null)||(Is(X,FValue::Int)&&FMath::Abs(X->I)<=1000),TEXT("PHYSICS_INVALID"));
  if(S==TEXT("delta")||S==TEXT("steps")||S==TEXT("blob_size"))return Uint(X)&&Require(S==TEXT("delta")?X->I<=1:S==TEXT("steps")?X->I<=256:X->I>0&&X->I<=8388608,TEXT("LIMIT"));
  if(S==TEXT("nullable_case"))return Require(Is(X,FValue::Null)||Str(X)==TEXT("weak")||Str(X)==TEXT("strong"),TEXT("SCHEMA"));
  if(S==TEXT("class"))return Require(Str(X)==TEXT("synthetic-contract-only")||Str(X)==TEXT("genesis-runtime"),TEXT("PROFILE"));
  if(S==TEXT("media"))return Require(Str(X)==TEXT("application/x-edgeworld-static-vector")||Str(X)==TEXT("application/x-genesis-gstraj;version=1.4.3"),TEXT("PROFILE"));
  if(S==TEXT("output"))return Require(Is(X,FValue::String)&&X->S.Len()<=1024,TEXT("SCHEMA"));
  if(S==TEXT("json_object"))return Require(Is(X,FValue::Object),TEXT("SCHEMA"));
  if(S==TEXT("i7_config"))return Require(Eq(X,Get(Schema,TEXT("physics_parameters"))),TEXT("PROFILE"));
  if(S==TEXT("signs"))return Require(Canon(X)==TEXT("[1,-1,1]"),TEXT("SCHEMA"));
  if(S==TEXT("vec3"))return Vec(X,3,TNumericLimits<double>::Max());
  if(S==TEXT("extent"))return IntVec(X,4)&&Require(Num(X->A[0])<Num(X->A[2])&&Num(X->A[1])<Num(X->A[3]),TEXT("GEOGRAPHY"));
  if(S==TEXT("polygon")||S==TEXT("polyline"))
  {
   if(!Require(Is(X,FValue::Array)&&X->A.Num()>=(S==TEXT("polygon")?4:2),TEXT("GEOGRAPHY")))return false;
   for(const V& P:X->A)if(!IntVec(P,2))return false;
   return Require(S!=TEXT("polygon")||Eq(X->A[0],X->A.Last()),TEXT("GEOGRAPHY"));
  }
  if(S==TEXT("ids")){if(!Require(Is(X,FValue::Array)&&X->A.Num()>=2&&X->A.Num()<=6,TEXT("GEOGRAPHY")))return false;TSet<FString> Seen;for(const V& C:X->A){if(!Identity(C)||!Require(!Seen.Contains(C->S),TEXT("ID")))return false;Seen.Add(C->S);}return true;}
  if(S==TEXT("assets")||S==TEXT("decorations")||S==TEXT("sources")||S==TEXT("dependencies")||S==TEXT("bindings")||S==TEXT("bodies")||S==TEXT("contacts"))return Entries(X,S);
  TArray<FString> Values;S.ParseIntoArray(Values,TEXT("|"));return Require(Is(X,FValue::String)&&Values.Contains(X->S),TEXT("SCHEMA"));
 }
 bool Entries(const V& X,const FString& K)
 {
  int32 Limit=K==TEXT("assets")?64:K==TEXT("decorations")?1000:K==TEXT("sources")?32:K==TEXT("dependencies")?16:K==TEXT("contacts")?32:2;
  if(!Require(Is(X,FValue::Array)&&X->A.Num()<=Limit,TEXT("LIMIT")))return false;
  TSet<FString> Seen;FString Last;int64 Total=0;int32 Index=0;
  for(const V& Item:X->A)
  {
   FString IdentityValue;
   if(K==TEXT("assets"))
   {
    if(!Keys(Item,TEXT("asset_id,uri,content_sha256,byte_count,source,use,license_status,dependencies"))||!Identity(Get(Item,TEXT("asset_id")))||!Hash(Get(Item,TEXT("content_sha256")))||!Uint(Get(Item,TEXT("byte_count"))))return false;
    IdentityValue=Str(Get(Item,TEXT("asset_id")));Total+=Num(Get(Item,TEXT("byte_count")));
    FString Uri=Str(Get(Item,TEXT("uri")));FString Path,Name;
    if(!Require(Uri.StartsWith(TEXT("/Engine/"))&&Uri.Split(TEXT("."),&Path,&Name)&&!Name.IsEmpty(),TEXT("ASSET")))return false;
    auto AssetChar=[](TCHAR C){return (C>='A'&&C<='Z')||(C>='a'&&C<='z')||(C>='0'&&C<='9')||C=='_';};
    for(TCHAR C:Path)if(!Require(C=='/'||AssetChar(C),TEXT("ASSET")))return false;for(TCHAR C:Name)if(!Require(AssetChar(C),TEXT("ASSET")))return false;
    if(!Require(Str(Get(Item,TEXT("source")))==TEXT("installed-ue-5.8.3-basicshapes")&&Str(Get(Item,TEXT("use")))==TEXT("technical-proxy-not-realism")&&Str(Get(Item,TEXT("license_status")))==TEXT("ue-installed-content-no-shipping-review"),TEXT("ASSET")))return false;
    V Deps=Get(Item,TEXT("dependencies"));if(!Require(Is(Deps,FValue::Array),TEXT("ASSET")))return false;TSet<FString> Ds;for(const V& D:Deps->A){if(!Identity(D)||!Require(!Ds.Contains(D->S),TEXT("ASSET")))return false;Ds.Add(D->S);}
    if(!Require((Last.IsEmpty()||OrdinalLess(Last,IdentityValue))&&Total<=2147483648LL,TEXT("ASSET")))return false;Last=IdentityValue;
   }
   else if(K==TEXT("decorations"))
   {
    if(!Keys(Item,TEXT("instance_id,place_id,asset_id,position_cm,scale_milli")))return false;
    for(const TCHAR* Key:{TEXT("instance_id"),TEXT("place_id"),TEXT("asset_id")})if(!Identity(Get(Item,Key)))return false;
    if(!IntVec(Get(Item,TEXT("position_cm")),3)||!IntVec(Get(Item,TEXT("scale_milli")),3))return false;
    for(const V& N:Get(Item,TEXT("scale_milli"))->A)if(!Require(N->I>0,TEXT("SCHEMA")))return false;IdentityValue=Str(Get(Item,TEXT("instance_id")));
   }
   else if(K==TEXT("sources"))
   {
    if(!Keys(Item,TEXT("path,sha256"))||!Hash(Get(Item,TEXT("sha256"))))return false;IdentityValue=Str(Get(Item,TEXT("path")));TArray<FString> Parts;IdentityValue.ParseIntoArray(Parts,TEXT("/"),false);
    if(!Require(Is(Get(Item,TEXT("path")),FValue::String)&&!IdentityValue.StartsWith(TEXT("/"))&&!Parts.Contains(TEXT("..")),TEXT("BUILD")))return false;
   }
   else if(K==TEXT("dependencies"))
   {
    if(!Keys(Item,TEXT("name,version,metadata_sha256"))||!Hash(Get(Item,TEXT("metadata_sha256")))||!Require(Is(Get(Item,TEXT("name")),FValue::String)&&Is(Get(Item,TEXT("version")),FValue::String),TEXT("BUILD")))return false;IdentityValue=Str(Get(Item,TEXT("name")));
   }
   else if(K==TEXT("bindings"))
   {
    if(!Keys(Item,TEXT("physical_id,existence_id,genesis_name,role,config_entity_index")))return false;for(const TCHAR* Key:{TEXT("physical_id"),TEXT("existence_id"),TEXT("genesis_name")})if(!Identity(Get(Item,Key)))return false;
    if(!Uint(Get(Item,TEXT("config_entity_index")))||!Require(Str(Get(Item,TEXT("role")))==TEXT("dynamic")||Str(Get(Item,TEXT("role")))==TEXT("support"),TEXT("PHYSICS_INVALID")))return false;IdentityValue=Str(Get(Item,TEXT("physical_id")));
   }
   else if(K==TEXT("bodies"))
   {
    if(!Keys(Item,TEXT("physical_id,position_m,quaternion_wxyz,linear_velocity_m_s,angular_velocity_rad_s,mass_kg"))||!Identity(Get(Item,TEXT("physical_id"))))return false;
    if(!Vec(Get(Item,TEXT("position_m")),3,10)||!Vec(Get(Item,TEXT("quaternion_wxyz")),4,1.001)||!Vec(Get(Item,TEXT("linear_velocity_m_s")),3,100)||!Vec(Get(Item,TEXT("angular_velocity_rad_s")),3,100))return false;
    double Norm=0,Mass;for(const V& C:Get(Item,TEXT("quaternion_wxyz"))->A){double D;F64(C,D);Norm+=D*D;}
    if(!Require(FMath::Abs(Norm-1)<=1e-4&&F64(Get(Item,TEXT("mass_kg")),Mass)&&Mass>0,TEXT("PHYSICS_INVALID")))return false;IdentityValue=Str(Get(Item,TEXT("physical_id")));
   }
   else
   {
    if(!Keys(Item,TEXT("pair,position_m,force_on_dynamic_n"))||!Require(Canon(Get(Item,TEXT("pair")))==TEXT("[\"body-dynamic\",\"body-support\"]"),TEXT("PHYSICS_INVALID"))||!Vec(Get(Item,TEXT("position_m")),3,10)||!Vec(Get(Item,TEXT("force_on_dynamic_n")),3,1e6))return false;
    // Same fixed pair for every contact, then lexical f64 bit-vector ordering.
    FString Order=Canon(Get(Item,TEXT("position_m")))+Canon(Get(Item,TEXT("force_on_dynamic_n")));
    if(!Require(Last.IsEmpty()||!OrdinalLess(Order,Last),TEXT("PHYSICS_INVALID")))return false;Last=Order;
   }
   if(K!=TEXT("contacts")){if(!Require(!Seen.Contains(IdentityValue),TEXT("ID")))return false;Seen.Add(IdentityValue);}
   if(K==TEXT("bindings")||K==TEXT("bodies"))if(!Require(IdentityValue==(Index==0?TEXT("body-dynamic"):TEXT("body-support")),TEXT("PHYSICS_INVALID")))return false;++Index;
  }
  return Require((K!=TEXT("bindings")&&K!=TEXT("bodies"))||Index==2,TEXT("PHYSICS_INVALID"));
 }
 V ExpectedRefs(const V& R)
 {
  FString K=Kind(R);V Shape=Make(FValue::Object);V Base=Get(Get(Schema,TEXT("refs")),*K);if(!Base)return {};
  if(K==TEXT("route")){V Ids=Get(Body(R),TEXT("place_ids"));if(!Is(Ids,FValue::Array))return {};for(int32 I=0;I<Ids->A.Num();++I){V S=Make(FValue::String);S->S=TEXT("place");Shape->O.Add(FString::Printf(TEXT("p%d"),I),S);}return Shape;}
  for(const auto& P:Base->O){FString Key=P.Key;Key.RemoveFromEnd(TEXT("?"));if(K==TEXT("manifest")&&Num(Get(Body(R),TEXT("revision")))==0&&Key!=TEXT("state"))continue;if(K==TEXT("event")&&Key==TEXT("prior_event")&&!Get(Refs(R),TEXT("prior_event")))continue;Shape->O.Add(Key,P.Value);}return Shape;
 }
 bool Record(const V& R)
 {
  if(!Tree(R)||!Keys(R,TEXT("domain,version,world_id,kind,id,body,refs"))||!Require(Str(Get(R,TEXT("domain")))==TEXT("edgeworld.universe.authority")&&Str(Get(R,TEXT("version")))==TEXT("0.2"),TEXT("DOMAIN"))||!Identity(Get(R,TEXT("world_id")))||!Identity(Get(R,TEXT("id"))))return false;
  FString K=Kind(R);V Shape=Get(Get(Schema,TEXT("body")),*K);if(!Require(!!Shape,TEXT("SCHEMA"))||!Exact(Body(R),Shape))return false;
  for(const auto& P:Shape->O)if(!Field(Get(Body(R),*P.Key),Str(P.Value)))return false;
  if(!Exact(Refs(R),ExpectedRefs(R)))return false;for(const auto& P:Refs(R)->O)if(!Hash(P.Value))return false;
  return Require(Canon(R).Len()<=Num(Get(Get(Schema,TEXT("kind_bytes")),*K)),TEXT("LIMIT"));
 }
 V Target(const V& R,const TCHAR* Key){const V* P=Records.Find(Str(Get(Refs(R),Key)));if(!P){Require(false,TEXT("PROOF"));return {};}return *P;}
 bool SameRef(const V& A,const TCHAR* AK,const V& B,const TCHAR* BK){return Eq(Get(Refs(A),AK),Get(Refs(B),BK));}
 bool Static(const V& R,const FEdgeWorldUniverseContext& C);
 bool Transition(const V& M);
 bool Verify(const V& Env,const FEdgeWorldUniverseExpectation& E,FEdgeWorldUniverseObservation& Out);
};
bool FValidator::Static(const V& R,const FEdgeWorldUniverseContext& C)
{
 V B=Body(R);FString K=Kind(R);auto T=[&](const TCHAR* Key){return Target(R,Key);};
 if(Get(B,TEXT("artifact_class"))&&!Require(Str(Get(B,TEXT("artifact_class")))==C.ArtifactClass,TEXT("PROFILE")))return false;
 if(K==TEXT("existence"))return Require(Eq(Get(R,TEXT("id")),Get(B,TEXT("existence_id"))),TEXT("ID"));
 if(K==TEXT("unit_transform")){double D;return Require(F64(Get(B,TEXT("scale")),D)&&D==100,TEXT("PHYSICS_INVALID"));}
 if(K==TEXT("provider_build"))return Require(Sha(Canon(R),true)==C.ExpectedBuild&&(C.ArtifactClass!=TEXT("genesis-runtime")||!Is(Get(B,TEXT("adapter_source_sha256")),FValue::Null)),TEXT("BUILD"));
 if(K==TEXT("resolved_options"))
 {
  bool Runtime=C.ArtifactClass==TEXT("genesis-runtime");if(!Require(Sha(Canon(R),true)==C.ExpectedOptions&&Str(Get(Refs(R),TEXT("build")))==C.ExpectedBuild&&Str(Get(B,TEXT("resolution")))==(Runtime?TEXT("runtime-exported"):TEXT("static-declared")),TEXT("BUILD")))return false;
  if(!Runtime&&!Require(Get(B,TEXT("exports"))->O.IsEmpty(),TEXT("BUILD")))return false;
  if(Runtime){V Ex=Get(B,TEXT("exports"));if(!Keys(Ex,TEXT("sim_options,rigid_options,dynamic_morph,support_morph,rigid_material")))return false;for(const auto& P:Ex->O)if(!Require(Is(P.Value,FValue::Object)&&P.Value->O.Num()>0,TEXT("BUILD")))return false;}return true;
 }
 if(K==TEXT("physics_config"))return Require(Str(Get(Refs(R),TEXT("build")))==C.ExpectedBuild&&Str(Get(Refs(R),TEXT("options")))==C.ExpectedOptions&&SameRef(T(TEXT("options")),TEXT("build"),R,TEXT("build"))&&Str(Get(Body(T(TEXT("options"))),TEXT("parameter_hash")))==Sha(Canon(Get(B,TEXT("config")))),TEXT("BUILD"));
 if(K==TEXT("physics_binding"))
 {
  V Entities=Get(Get(Body(T(TEXT("config"))),TEXT("config")),TEXT("entities"));V Bindings=Get(B,TEXT("bindings"));if(!Require(Is(Entities,FValue::Array)&&Entities->A.Num()==2,TEXT("PHYSICS_INVALID")))return false;
  for(int32 I=0;I<2;++I){V Entry=Bindings->A[I],Entity=Entities->A[I];for(const TCHAR* Key:{TEXT("physical_id"),TEXT("existence_id"),TEXT("genesis_name")})if(!Require(Eq(Get(Entry,Key),Get(Entity,Key)),TEXT("PHYSICS_INVALID")))return false;
   if(!Require(Num(Get(Entry,TEXT("config_entity_index")))==I&&Str(Get(Entry,TEXT("role")))==(I==0?TEXT("dynamic"):TEXT("support")),TEXT("PHYSICS_INVALID")))return false;
   V Exists=Body(T(I==0?TEXT("dynamic_exists"):TEXT("support_exists")));if(!Require(Eq(Get(Exists,TEXT("existence_id")),Get(Entry,TEXT("existence_id")))&&Str(Get(Exists,TEXT("category")))==TEXT("physical"),TEXT("REFERENCE")))return false;
  }return true;
 }
 if(K==TEXT("physics_sample")||K==TEXT("checkpoint_descriptor")||K==TEXT("physics_snapshot"))
 {
  if(!Require(SameRef(T(TEXT("binding")),TEXT("config"),R,TEXT("config")),TEXT("PHYSICS_INVALID")))return false;
  if(K==TEXT("checkpoint_descriptor"))
  {
   bool Syn=C.ArtifactClass==TEXT("synthetic-contract-only");return Require(Str(Get(B,TEXT("format")))==(Syn?TEXT("synthetic-static-bytes"):TEXT("genesis-gstraj"))&&Str(Get(B,TEXT("media_type")))==(Syn?TEXT("application/x-edgeworld-static-vector"):TEXT("application/x-genesis-gstraj;version=1.4.3"))&&SameRef(R,TEXT("build"),T(TEXT("config")),TEXT("build")),TEXT("PROFILE"));
  }
  if(K==TEXT("physics_snapshot")){for(const TCHAR* Name:{TEXT("sample"),TEXT("checkpoint")})if(!Require(SameRef(T(Name),TEXT("config"),R,TEXT("config"))&&SameRef(T(Name),TEXT("binding"),R,TEXT("binding")),TEXT("PHYSICS_INVALID")))return false;return Require((Str(Get(B,TEXT("case_id")))==TEXT("initial"))==(Num(Get(B,TEXT("physical_step_count")))==0),TEXT("PHYSICS_INVALID"));}
  return true;
 }
 if(K==TEXT("place"))return Require(Str(Get(Body(T(TEXT("existence"))),TEXT("category")))==TEXT("place"),TEXT("REFERENCE"));
 if(K==TEXT("route")){V Ids=Get(B,TEXT("place_ids"));for(int32 I=0;I<Ids->A.Num();++I)if(!Require(Eq(Get(Body(T(*FString::Printf(TEXT("p%d"),I))),TEXT("place_id")),Ids->A[I]),TEXT("GEOGRAPHY")))return false;return true;}
 if(K==TEXT("watercourse"))return Require(Str(Get(Body(T(TEXT("upstream"))),TEXT("place_kind")))==TEXT("forest")&&Str(Get(Body(T(TEXT("marsh"))),TEXT("place_kind")))==TEXT("river_marsh")&&Str(Get(Body(T(TEXT("outlet"))),TEXT("place_kind")))==TEXT("ocean"),TEXT("GEOGRAPHY"));
 if(K==TEXT("asset_manifest"))
 {
  V EntriesValue=Get(B,TEXT("entries"));TMap<FString,V> Assets;for(const V& A:EntriesValue->A)Assets.Add(Str(Get(A,TEXT("asset_id"))),A);
  TSet<FString> Active,Done;TFunction<bool(const FString&)> Visit=[&](const FString& Name){if(!Require(Assets.Contains(Name)&&!Active.Contains(Name),TEXT("ASSET")))return false;if(Done.Contains(Name))return true;Active.Add(Name);for(const V& D:Get(Assets[Name],TEXT("dependencies"))->A)if(!Visit(D->S))return false;Active.Remove(Name);Done.Add(Name);return true;};
  for(const auto& A:Assets)if(!Visit(A.Key))return false;
  return Require(Str(Get(B,TEXT("dependency_status")))==(C.ArtifactClass==TEXT("synthetic-contract-only")?TEXT("declared-static"):TEXT("runtime-resolved")),TEXT("ASSET"));
 }
 if(K==TEXT("projection"))
 {
  TSet<FString> Assets;for(const V& A:Get(Body(T(TEXT("assets"))),TEXT("entries"))->A)Assets.Add(Str(Get(A,TEXT("asset_id"))));
  for(const V& D:Get(B,TEXT("decorations"))->A)if(!Require(Assets.Contains(Str(Get(D,TEXT("asset_id")))),TEXT("ASSET")))return false;return true;
 }
 if(K==TEXT("world_manifest"))
 {
  if(!Require(Str(Get(Body(T(TEXT("world_existence"))),TEXT("category")))==TEXT("world"),TEXT("GEOGRAPHY")))return false;
  TSet<FString> Places,Exists;for(const TCHAR* Key:{TEXT("world_existence"),TEXT("dynamic_existence"),TEXT("support_existence")})Exists.Add(Str(Get(Body(T(Key)),TEXT("existence_id"))));
  V Bounds=Get(B,TEXT("extent_cm"));auto InBounds=[&](const V& Points){for(const V& P:Points->A)if(!Require(Num(P->A[0])>=Num(Bounds->A[0])&&Num(P->A[0])<=Num(Bounds->A[2])&&Num(P->A[1])>=Num(Bounds->A[1])&&Num(P->A[1])<=Num(Bounds->A[3]),TEXT("GEOGRAPHY")))return false;return true;};
  for(const TCHAR* Name:{TEXT("city"),TEXT("wildland"),TEXT("plain"),TEXT("forest"),TEXT("river_marsh"),TEXT("ocean")})
  {
   V P=T(Name);if(!Require(Str(Get(Body(P),TEXT("place_kind")))==Name,TEXT("GEOGRAPHY")))return false;
   Places.Add(Str(Get(Body(P),TEXT("place_id"))));Exists.Add(Str(Get(Body(Target(P,TEXT("existence"))),TEXT("existence_id"))));if(!InBounds(Get(Body(P),TEXT("footprint_cm"))))return false;
  }
  if(!Require(Places.Num()==6&&Exists.Num()==9,TEXT("ID")))return false;
  auto RouteIds=[&](const TCHAR* Ref,std::initializer_list<const TCHAR*> Names){V A=Get(Body(T(Ref)),TEXT("place_ids"));if(!Require(A->A.Num()==int32(Names.size()),TEXT("GEOGRAPHY")))return false;int32 I=0;for(const TCHAR* Name:Names)if(!Require(Eq(A->A[I++],Get(Body(T(Name)),TEXT("place_id"))),TEXT("GEOGRAPHY")))return false;return true;};
  if(!RouteIds(TEXT("main_route"),{TEXT("city"),TEXT("plain"),TEXT("forest"),TEXT("river_marsh"),TEXT("ocean")})||!RouteIds(TEXT("branch_route"),{TEXT("forest"),TEXT("wildland")}))return false;
  int32 Points=0;for(const TCHAR* Ref:{TEXT("main_route"),TEXT("branch_route"),TEXT("watercourse")}){V P=Get(Body(T(Ref)),TEXT("polyline_cm"));Points+=P->A.Num();if(!InBounds(P))return false;}
  for(const TCHAR* Ref:{TEXT("city"),TEXT("wildland"),TEXT("plain"),TEXT("forest"),TEXT("river_marsh"),TEXT("ocean")})Points+=Get(Body(T(Ref)),TEXT("footprint_cm"))->A.Num();
  if(!Require(Points<=4096,TEXT("LIMIT")))return false;
  for(const V& D:Get(Body(T(TEXT("projection"))),TEXT("decorations"))->A)if(!Require(Places.Contains(Str(Get(D,TEXT("place_id")))),TEXT("GEOGRAPHY")))return false;return true;
 }
 if(K==TEXT("state"))
 {
  V World=T(TEXT("world")),Binding=Target(T(TEXT("snapshot")),TEXT("binding"));return Require(SameRef(Binding,TEXT("dynamic_exists"),World,TEXT("dynamic_existence"))&&SameRef(Binding,TEXT("support_exists"),World,TEXT("support_existence")),TEXT("REFERENCE"));
 }
 if(K==TEXT("intent"))
 {
  bool Retain=Str(Get(B,TEXT("action")))==TEXT("retain_snapshot");return Require(Retain?(Num(Get(B,TEXT("tick_delta")))==0&&Is(Get(B,TEXT("case_id")),FValue::Null)&&Num(Get(B,TEXT("budget")))==0):(Num(Get(B,TEXT("tick_delta")))==1&&(Str(Get(B,TEXT("case_id")))==TEXT("weak")||Str(Get(B,TEXT("case_id")))==TEXT("strong"))),TEXT("TRANSITION"));
 }
 return true;
}
bool FValidator::Transition(const V& M)
{
 V S=Target(M,TEXT("state")),B=Body(M),SB=Body(S),Snap=Target(S,TEXT("snapshot"));
 if(!Require(Eq(Get(B,TEXT("tick")),Get(SB,TEXT("tick")))&&Eq(Get(B,TEXT("revision")),Get(SB,TEXT("revision")))&&Eq(Get(B,TEXT("watermark")),Get(SB,TEXT("revision"))),TEXT("WATERMARK")))return false;
 if(Num(Get(B,TEXT("revision")))==0)return Require(Num(Get(B,TEXT("tick")))==0&&Is(Get(SB,TEXT("development_mm")),FValue::Null)&&Num(Get(SB,TEXT("random_cursor")))==0&&Num(Get(SB,TEXT("budget")))==8&&Str(Get(Body(Snap),TEXT("case_id")))==TEXT("initial")&&Num(Get(Body(Snap),TEXT("physical_step_count")))==0,TEXT("HEAD"));
 V Prior=Target(M,TEXT("prior_manifest")),Previous=Target(Prior,TEXT("state")),PB=Body(Previous),Event=Target(M,TEXT("event")),Index=Target(M,TEXT("index")),Result=Target(Index,TEXT("result")),Admission=Target(Event,TEXT("admission")),Command=Target(Admission,TEXT("command")),Candidate=Target(Admission,TEXT("candidate")),Intent=Target(Command,TEXT("intent")),IB=Body(Intent),Approval=Target(Command,TEXT("approval")),Proposal=Target(Command,TEXT("proposal")),CB=Body(Candidate),Before=Target(Previous,TEXT("snapshot"));
 if(!Error.IsEmpty())return false;
 if(!Require(Num(Get(B,TEXT("revision")))==Num(Get(Body(Prior),TEXT("revision")))+1&&SameRef(S,TEXT("world"),Previous,TEXT("world"))&&SameRef(Event,TEXT("state"),M,TEXT("state"))&&SameRef(Result,TEXT("state"),M,TEXT("state"))&&SameRef(Result,TEXT("event"),M,TEXT("event")),TEXT("HEAD")))return false;
 V PriorEvent=Get(Refs(Prior),TEXT("event")),EventPrior=Get(Refs(Event),TEXT("prior_event"));
 if(!Require((!PriorEvent&&!EventPrior)||Eq(PriorEvent,EventPrior),TEXT("HEAD")))return false;
 if(!Require(SameRef(Candidate,TEXT("prior_state"),Prior,TEXT("state"))&&SameRef(Candidate,TEXT("command"),Admission,TEXT("command"))&&SameRef(Result,TEXT("command"),Admission,TEXT("command"))&&SameRef(Candidate,TEXT("snapshot"),S,TEXT("snapshot"))&&SameRef(Result,TEXT("checkpoint"),S,TEXT("snapshot")),TEXT("REFERENCE")))return false;
 FString Principal=Str(Get(IB,TEXT("principal")));
 if(!Require(SameRef(Approval,TEXT("proposal"),Command,TEXT("proposal"))&&SameRef(Approval,TEXT("intent"),Command,TEXT("intent"))&&Str(Get(Body(Proposal),TEXT("principal")))==Principal&&Str(Get(Body(Approval),TEXT("principal")))==Principal&&Str(Get(Body(Admission),TEXT("principal")))==Principal,TEXT("AUTHORIZATION")))return false;
 if(!Require(Num(Get(IB,TEXT("expected_revision")))==Num(Get(PB,TEXT("revision")))&&Eq(Get(IB,TEXT("expected_revision")),Get(Body(Admission),TEXT("evaluated_revision")))&&Eq(Get(IB,TEXT("random_cursor")),Get(PB,TEXT("random_cursor")))&&Num(Get(IB,TEXT("expected_revision")))<=Num(Get(Body(Approval),TEXT("expires_revision"))),TEXT("AUTHORIZATION")))return false;
 if(!Require(Eq(Get(CB,TEXT("revision")),Get(SB,TEXT("revision")))&&Eq(Get(CB,TEXT("tick")),Get(SB,TEXT("tick")))&&Eq(Get(CB,TEXT("influence_mm")),Get(SB,TEXT("development_mm"))),TEXT("TRANSITION")))return false;
 for(const TCHAR* Key:{TEXT("config"),TEXT("binding")})if(!Require(SameRef(Intent,Key,Snap,Key)&&SameRef(Before,Key,Snap,Key),TEXT("PHYSICS_INVALID")))return false;
 if(Str(Get(IB,TEXT("action")))==TEXT("retain_snapshot"))
 {
  if(!Require(Num(Get(IB,TEXT("tick_delta")))==0&&Is(Get(IB,TEXT("case_id")),FValue::Null)&&Num(Get(IB,TEXT("budget")))==0&&Str(Get(CB,TEXT("adapter_kind")))==TEXT("checkpoint_reuse")&&SameRef(Previous,TEXT("snapshot"),S,TEXT("snapshot")),TEXT("TRANSITION")))return false;
  for(const TCHAR* Key:{TEXT("tick"),TEXT("development_mm"),TEXT("budget"),TEXT("random_cursor")})if(!Require(Eq(Get(SB,Key),Get(PB,Key)),TEXT("TRANSITION")))return false;
 }
 else
 {
  V OldSample=Target(Before,TEXT("sample")),NewSample=Target(Snap,TEXT("sample"));double Dummy;uint64 OldBits=0,NewBits=0;
  V OldBodies=Get(Body(OldSample),TEXT("bodies")),NewBodies=Get(Body(NewSample),TEXT("bodies"));
  if(!Require(Is(OldBodies,FValue::Array)&&Is(NewBodies,FValue::Array)&&OldBodies->A.Num()==2&&NewBodies->A.Num()==2,TEXT("PHYSICS_INVALID")))return false;
  F64(Get(OldBodies->A[0],TEXT("position_m"))->A[2],Dummy,&OldBits);F64(Get(NewBodies->A[0],TEXT("position_m"))->A[2],Dummy,&NewBits);int64 D=0;
  if(!Require(Influence(OldBits,NewBits,D)&&Num(Get(SB,TEXT("development_mm")))==D&&Num(Get(IB,TEXT("tick_delta")))==1&&(Str(Get(IB,TEXT("case_id")))==TEXT("weak")||Str(Get(IB,TEXT("case_id")))==TEXT("strong"))&&Str(Get(CB,TEXT("adapter_kind")))==TEXT("genesis")&&Num(Get(SB,TEXT("tick")))==Num(Get(PB,TEXT("tick")))+1&&Eq(Get(Body(Snap),TEXT("case_id")),Get(IB,TEXT("case_id")))&&Num(Get(Body(Snap),TEXT("physical_step_count")))==Num(Get(Body(Before),TEXT("physical_step_count")))+8&&Num(Get(SB,TEXT("budget")))==Num(Get(PB,TEXT("budget")))-Num(Get(IB,TEXT("budget")))&&Num(Get(SB,TEXT("random_cursor")))==Num(Get(PB,TEXT("random_cursor")))+1,TEXT("TRANSITION")))return false;
 }
 V RB=Body(Result);if(!Require(Eq(Get(RB,TEXT("command_id")),Get(IB,TEXT("command_id")))&&Eq(Get(RB,TEXT("tick")),Get(SB,TEXT("tick")))&&Eq(Get(RB,TEXT("revision")),Get(SB,TEXT("revision")))&&Eq(Get(RB,TEXT("watermark")),Get(SB,TEXT("revision"))),TEXT("WATERMARK")))return false;
 return Require(Eq(Get(Body(Index),TEXT("command_id")),Get(IB,TEXT("command_id")))&&Eq(Get(Body(Index),TEXT("fingerprint")),Get(Refs(Result),TEXT("command"))),TEXT("COMMAND_CONFLICT"));
}
static FVector3d Vector(const V& X){double D[3]={};for(int32 I=0;I<3;++I)F64(X->A[I],D[I]);return FVector3d(D[0],D[1],D[2]);}
static TArray<FEdgeWorldUniverseBody> Bodies(const V& Sample)
{
 TArray<FEdgeWorldUniverseBody> Result;for(const V& X:Get(Body(Sample),TEXT("bodies"))->A){FEdgeWorldUniverseBody B;B.PhysicalId=Str(Get(X,TEXT("physical_id")));B.PositionM=Vector(Get(X,TEXT("position_m")));B.LinearVelocityMS=Vector(Get(X,TEXT("linear_velocity_m_s")));B.AngularVelocityRadS=Vector(Get(X,TEXT("angular_velocity_rad_s")));V Q=Get(X,TEXT("quaternion_wxyz"));double D[4]={};for(int32 I=0;I<4;++I)F64(Q->A[I],D[I]);B.QuaternionWXYZ=FVector4d(D[0],D[1],D[2],D[3]);F64(Get(X,TEXT("mass_kg")),B.MassKg);Result.Add(B);}return Result;
}
static bool SameContext(const FEdgeWorldUniverseContext& A,const FEdgeWorldUniverseContext& B){return A.WorldId==B.WorldId&&A.AuthorityRoot==B.AuthorityRoot&&A.TrustAlgorithm==B.TrustAlgorithm&&A.TrustAnchor==B.TrustAnchor&&A.ArtifactClass==B.ArtifactClass&&A.ExpectedBuild==B.ExpectedBuild&&A.ExpectedOptions==B.ExpectedOptions;}
static bool CanonicalRoot(const FString& Root){if(!Root.StartsWith(TEXT("/"))||Root.StartsWith(TEXT("//"))||(Root.Len()>1&&Root.EndsWith(TEXT("/")))||Root.Contains(TEXT("//")))return false;TArray<FString> P;Root.ParseIntoArray(P,TEXT("/"));for(TCHAR C:Root)if(C==0)return false;return !P.Contains(TEXT("."))&&!P.Contains(TEXT(".."));}
bool FValidator::Verify(const V& Env,const FEdgeWorldUniverseExpectation& E,FEdgeWorldUniverseObservation& Out)
{
 const auto& C=E.Context;const auto& H=E.TrustedHead;
 if(!Require(CanonicalRoot(C.AuthorityRoot)&&C.AuthorityRoot==H.Context.AuthorityRoot,TEXT("ROOT_MISMATCH"))||!Require(SameContext(C,H.Context),TEXT("AUTHORIZATION")))return false;
 if(!Require(Id(C.WorldId)&&Id(E.RequestId)&&LowerHex(C.TrustAnchor,64)&&LowerHex(C.ExpectedBuild,64)&&LowerHex(C.ExpectedOptions,64)&&LowerHex(H.Head,64)&&C.TrustAlgorithm==TEXT("local-hmac-sha256.v0.2")&&H.Domain==TEXT("edgeworld.universe.authority")&&H.Version==TEXT("0.2")&&H.Profile==TEXT("composite-rigid-support.v0.2")&&(H.StorageState==TEXT("ready")||H.StorageState==TEXT("unconfirmed_readonly"))&&C.ArtifactClass==(E.bFixtureOnly?TEXT("synthetic-contract-only"):TEXT("genesis-runtime")),TEXT("PROFILE")))return false;
 if(!Require(E.Tick>=0&&E.Tick<=MaxInt&&E.Revision>=0&&E.Revision<=MaxInt&&E.Watermark==E.Revision,TEXT("WATERMARK")))return false;
 if(!Keys(Env,TEXT("protocol_version,request_id,ok,result"))||!Require(Num(Get(Env,TEXT("protocol_version")))==1&&Is(Get(Env,TEXT("ok")),FValue::Bool)&&Get(Env,TEXT("ok"))->B,TEXT("SCHEMA"))||!Require(Str(Get(Env,TEXT("request_id")))==E.RequestId,TEXT("PROOF")))return false;
 V R=Get(Env,TEXT("result"));if(!Keys(R,TEXT("domain,version,world_id,operation,payload"))||!Require(Str(Get(R,TEXT("domain")))==H.Domain&&Str(Get(R,TEXT("version")))==H.Version,TEXT("DOMAIN"))||!Require(Str(Get(R,TEXT("world_id")))==C.WorldId&&Str(Get(R,TEXT("operation")))==TEXT("observe"),TEXT("WORLD")))return false;
 V P=Get(R,TEXT("payload"));if(!Keys(P,TEXT("manifest,state,event,watermark,storage_state,artifact_class,head,membership,records,opaque_refs"))||!Require(Str(Get(P,TEXT("storage_state")))==H.StorageState&&Str(Get(P,TEXT("artifact_class")))==C.ArtifactClass&&Str(Get(P,TEXT("head")))==H.Head,TEXT("PROOF"))||!Require(Num(Get(P,TEXT("watermark")))==E.Watermark,TEXT("WATERMARK")))return false;
 V Ms=Get(P,TEXT("membership")),Aux=Get(P,TEXT("records")),Opaque=Get(P,TEXT("opaque_refs")),M=Get(P,TEXT("manifest")),S=Get(P,TEXT("state")),Event=Get(P,TEXT("event"));
 if(!Require(Is(Ms,FValue::Array)&&Ms->A.Num()>=1&&Ms->A.Num()<=64&&Is(Aux,FValue::Array)&&Aux->A.Num()<=96&&Is(Opaque,FValue::Array)&&Opaque->A.Num()<=256,TEXT("PROOF_LIMIT")))return false;
 TArray<V> All=Ms->A;All.Append(Aux->A);All.Add(M);All.Add(S);if(!Is(Event,FValue::Null))All.Add(Event);
 TMap<FString,FString> Identities;TMap<FString,int32> Counts;
 for(const V& X:All)
 {
  if(!Record(X)||!Require(Str(Get(X,TEXT("world_id")))==C.WorldId,TEXT("WORLD")))return false;
  FString D=Sha(Canon(X),true),IdentityKey=Kind(X)+TEXT(":")+Str(Get(X,TEXT("id")));if(!Require(!D.IsEmpty(),TEXT("HASH")))return false;
  if(!Require(!Identities.Contains(IdentityKey)||Identities[IdentityKey]==D,TEXT("ID")))return false;Identities.Add(IdentityKey,D);Records.Add(D,X);Counts.FindOrAdd(Kind(X))++;
 }
 for(const auto& Pair:Records)
 {
  V ER=ExpectedRefs(Pair.Value);for(const auto& Ref:Refs(Pair.Value)->O){const V* T=Records.Find(Ref.Value->S);if(T&&!Require(Kind(*T)==Str(Get(ER,*Ref.Key)),TEXT("PROOF")))return false;}
 }
 for(const auto& Cnt:Counts)if(!Require(Cnt.Value<=Num(Get(Get(Schema,TEXT("proof_kind_max")),*Cnt.Key)),TEXT("PROOF_LIMIT")))return false;
 FString Selected=Sha(Canon(M),true);TSet<FString> Explicit;Explicit.Add(Selected);Explicit.Add(Sha(Canon(S),true));if(!Is(Event,FValue::Null))Explicit.Add(Sha(Canon(Event),true));
 for(const V& X:Ms->A){FString D=Sha(Canon(X),true);if(!Require(Kind(X)==TEXT("manifest")&&!Membership.Contains(D),TEXT("PROOF")))return false;Membership.Add(D);Explicit.Add(D);}
 TSet<FString> AuxSet;for(const V& X:Aux->A){FString D=Sha(Canon(X),true);if(!Require(!AuxSet.Contains(D)&&!Explicit.Contains(D),TEXT("PROOF")))return false;AuxSet.Add(D);}
 if(!Require(Sha(Canon(Ms->A[0]),true)==H.Head&&Sha(Canon(Ms->A.Last()),true)==Selected,TEXT("PROOF")))return false;
 for(int32 I=0;I<Ms->A.Num();++I){V A=Ms->A[I];if(!Require(Eq(Get(Body(A),TEXT("watermark")),Get(Body(A),TEXT("revision"))),TEXT("WATERMARK")))return false;if(I+1==Ms->A.Num())break;V B=Ms->A[I+1];int64 Delta=Num(Get(Body(A),TEXT("tick")))-Num(Get(Body(B),TEXT("tick")));if(!Require(Str(Get(Refs(A),TEXT("prior_manifest")))==Sha(Canon(B),true)&&Num(Get(Body(A),TEXT("revision")))==Num(Get(Body(B),TEXT("revision")))+1&&(Delta==0||Delta==1),TEXT("PROOF")))return false;}
 if(!Require(Kind(M)==TEXT("manifest")&&Kind(S)==TEXT("state")&&Num(Get(Body(M),TEXT("tick")))==E.Tick&&Num(Get(Body(M),TEXT("revision")))==E.Revision&&Num(Get(Body(M),TEXT("watermark")))==E.Watermark&&Str(Get(Refs(M),TEXT("state")))==Sha(Canon(S),true),TEXT("WATERMARK")))return false;
 if(!Require((E.Revision==0&&Is(Event,FValue::Null))||(E.Revision>0&&Kind(Event)==TEXT("event")&&Str(Get(Refs(M),TEXT("event")))==Sha(Canon(Event),true)),TEXT("PROOF")))return false;
 FString Previous=Str(Get(Refs(M),TEXT("prior_manifest")));TSet<FString> Active,Done;
 TFunction<bool(const FString&,bool)> Expand=[&](const FString& D,bool Prev)
 {
  FString Memo=D+(Prev?TEXT(":p"):TEXT(":n"));if(!Require(Records.Contains(D)&&!Active.Contains(Memo),TEXT("PROOF")))return false;if(Done.Contains(Memo))return true;Active.Add(Memo);Needed.Add(D);V X=Records[D];
  for(const auto& Ref:Refs(X)->O){if(Kind(X)==TEXT("manifest")&&(Ref.Key==TEXT("prior_manifest")||(Prev&&Ref.Key!=TEXT("state"))))continue;if(Kind(X)==TEXT("event")&&Ref.Key==TEXT("prior_event"))continue;if(!Expand(Ref.Value->S,false))return false;}
  Active.Remove(Memo);Done.Add(Memo);return true;
 };
 if(!Expand(Selected,false)||(!Previous.IsEmpty()&&!Expand(Previous,true)))return false;
 for(const auto& X:Records)if(!Require(Needed.Contains(X.Key)||Membership.Contains(X.Key),TEXT("PROOF")))return false;
 TSet<FString> Omitted;
 for(const auto& X:Records)
 {
  for(const auto& Ref:Refs(X.Value)->O)if(!Records.Contains(Ref.Value->S))
  {
   bool Allowed=(Kind(X.Value)==TEXT("event")&&Ref.Key==TEXT("prior_event"))||(Kind(X.Value)==TEXT("manifest")&&X.Key!=Selected&&Ref.Key!=TEXT("state"))||(Kind(X.Value)==TEXT("manifest")&&Membership.Contains(X.Key)&&X.Key!=Selected&&X.Key!=Previous);
   if(!Require(Allowed,TEXT("PROOF")))return false;Omitted.Add(Ref.Value->S);
  }
 }
 TArray<FString> Sorted=Omitted.Array();Sorted.Sort();if(!Require(Sorted.Num()==Opaque->A.Num(),TEXT("PROOF")))return false;for(int32 I=0;I<Sorted.Num();++I)if(!Require(Str(Opaque->A[I])==Sorted[I],TEXT("PROOF")))return false;
 // Membership-only ancestors are not renderable dependencies. Never validate them by expanding opaque history.
 for(const FString& D:Needed){V X=Records[D];if(Kind(X)==TEXT("event")||Kind(X)==TEXT("candidate")||Kind(X)==TEXT("command")||Kind(X)==TEXT("approval")||Kind(X)==TEXT("admission")||Kind(X)==TEXT("result")||Kind(X)==TEXT("index")||Kind(X)==TEXT("manifest"))continue;if(!Static(X,C))return false;}
 if(!Transition(M)||!Error.IsEmpty())return false;
 Out.WorldId=C.WorldId;Out.Manifest=Selected;Out.State=Sha(Canon(S),true);Out.Event=Is(Event,FValue::Null)?FString():Sha(Canon(Event),true);Out.StorageState=H.StorageState;Out.ArtifactClass=C.ArtifactClass;Out.Tick=E.Tick;Out.Revision=E.Revision;Out.Watermark=E.Watermark;Out.Budget=Num(Get(Body(S),TEXT("budget")));Out.RandomCursor=Num(Get(Body(S),TEXT("random_cursor")));if(Is(Get(Body(S),TEXT("development_mm")),FValue::Int))Out.DevelopmentMm=Num(Get(Body(S),TEXT("development_mm")));
 V Snapshot=Target(S,TEXT("snapshot")),Sample=Target(Snapshot,TEXT("sample")),World=Target(S,TEXT("world")),Projection=Target(World,TEXT("projection")),Transform=Target(Projection,TEXT("transform"));
 auto Points=[](const V& Values){TArray<FEdgeWorldUniversePoint> Result;for(const V& P:Values->A){FEdgeWorldUniversePoint Point;Point.X=Num(P->A[0]);Point.Y=Num(P->A[1]);Result.Add(Point);}return Result;};
 Out.WorldManifest=Sha(Canon(World),true);Out.Snapshot=Sha(Canon(Snapshot),true);Out.Config=Str(Get(Refs(Snapshot),TEXT("config")));Out.Binding=Str(Get(Refs(Snapshot),TEXT("binding")));Out.Build=C.ExpectedBuild;Out.Options=C.ExpectedOptions;Out.Transform=Sha(Canon(Transform),true);
 for(const TCHAR* Name:{TEXT("city"),TEXT("wildland"),TEXT("plain"),TEXT("forest"),TEXT("river_marsh"),TEXT("ocean")}){V Place=Target(World,Name);FEdgeWorldUniversePlace D;D.PlaceId=Str(Get(Body(Place),TEXT("place_id")));D.PlaceKind=Str(Get(Body(Place),TEXT("place_kind")));D.ExistenceDigest=Str(Get(Refs(Place),TEXT("existence")));D.ElevationCm=Num(Get(Body(Place),TEXT("elevation_cm")));D.FootprintCm=Points(Get(Body(Place),TEXT("footprint_cm")));Out.Places.Add(D);}
 for(const TCHAR* Name:{TEXT("main_route"),TEXT("branch_route")}){V Route=Target(World,Name);FEdgeWorldUniverseRoute D;D.Id=Str(Get(Body(Route),TEXT("route_id")));for(const V& IdValue:Get(Body(Route),TEXT("place_ids"))->A)D.PlaceIds.Add(IdValue->S);D.PolylineCm=Points(Get(Body(Route),TEXT("polyline_cm")));Out.Routes.Add(D);}
 Out.WatercourseCm=Points(Get(Body(Target(World,TEXT("watercourse"))),TEXT("polyline_cm")));
 V Assets=Target(Projection,TEXT("assets"));Out.AssetDependencyStatus=Str(Get(Body(Assets),TEXT("dependency_status")));
 for(const V& X:Get(Body(Assets),TEXT("entries"))->A){FEdgeWorldUniverseAsset A;A.AssetId=Str(Get(X,TEXT("asset_id")));A.Uri=Str(Get(X,TEXT("uri")));A.Sha256=Str(Get(X,TEXT("content_sha256")));A.ByteCount=Num(Get(X,TEXT("byte_count")));for(const V& Dep:Get(X,TEXT("dependencies"))->A)A.Dependencies.Add(Dep->S);Out.Assets.Add(A);}
 for(const V& X:Get(Body(Projection),TEXT("decorations"))->A){FEdgeWorldUniverseDecoration D;D.InstanceId=Str(Get(X,TEXT("instance_id")));D.PlaceId=Str(Get(X,TEXT("place_id")));D.AssetId=Str(Get(X,TEXT("asset_id")));for(int32 I=0;I<3;++I){D.PositionCm[I]=Num(Get(X,TEXT("position_cm"))->A[I]);D.ScaleMilli[I]=Num(Get(X,TEXT("scale_milli"))->A[I]);}Out.Decorations.Add(D);}
 Out.PhysicalStepCount=Num(Get(Body(Snapshot),TEXT("physical_step_count")));Out.Bodies=Bodies(Sample);Out.OriginCm=Vector(Get(Body(Transform),TEXT("origin_cm")));F64(Get(Body(Transform),TEXT("scale")),Out.Scale);F64(Get(Body(Projection),TEXT("development_cm_per_mm")),Out.DevelopmentCmPerMm);
 for(const V& Contact:Get(Body(Sample),TEXT("contacts"))->A){FEdgeWorldUniverseContact D;D.PositionM=Vector(Get(Contact,TEXT("position_m")));D.ForceOnDynamicN=Vector(Get(Contact,TEXT("force_on_dynamic_n")));Out.Contacts.Add(D);}
 if(!Previous.IsEmpty()){V PS=Target(Records[Previous],TEXT("state"));Out.PriorBodies=Bodies(Target(Target(PS,TEXT("snapshot")),TEXT("sample")));}
 Sorted=Needed.Array();Sorted.Sort();for(const FString& D:Sorted){V X=Records[D];FEdgeWorldUniverseRecord ROut;ROut.Digest=D;ROut.Kind=Kind(X);ROut.Id=Str(Get(X,TEXT("id")));ROut.CanonicalJson=Canon(X);Out.SelectedRecords.Add(ROut);}return Error.IsEmpty();
}
} // namespace EdgeUniverse

bool FEdgeWorldUniverseObservationParser::Verify(TArrayView<const uint8> Raw,const FEdgeWorldUniverseExpectation& E,FEdgeWorldUniverseObservation& Out,FString& Error)
{
 Out=FEdgeWorldUniverseObservation();Error.Reset();EdgeUniverse::FReader Reader(Raw);auto Root=Reader.Parse(true);if(!Root){Error=Reader.Error;return false;}EdgeUniverse::FValidator Validator;FEdgeWorldUniverseObservation Candidate;if(!Validator.Error.IsEmpty()||!Validator.Verify(Root,E,Candidate)){Error=Validator.Error;return false;}Candidate.WireBytes=Raw.Num()-(Raw.Num()>0&&Raw.Last()=='\n'?1:0);Out=MoveTemp(Candidate);return true;
}
bool FEdgeWorldUniverseObservationParser::CanonicalRecord(TArrayView<const uint8> Raw,FString& Canonical,FString& Digest,FString& Error)
{
 Canonical.Reset();Digest.Reset();Error.Reset();EdgeUniverse::FReader Reader(Raw);auto Root=Reader.Parse(false);if(!Root){Error=Reader.Error;return false;}EdgeUniverse::FValidator Validator;if(!Validator.Error.IsEmpty()||!Validator.Record(Root)){Error=Validator.Error;return false;}Canonical=EdgeUniverse::Canon(Root);Digest=EdgeUniverse::Sha(Canonical,true);if(Digest.IsEmpty()){Canonical.Reset();Error=TEXT("HASH");return false;}return true;
}
bool FEdgeWorldUniverseObservationParser::ExactInfluence(uint64 A,uint64 B,int64& Millimetres){return EdgeUniverse::Influence(A,B,Millimetres);}

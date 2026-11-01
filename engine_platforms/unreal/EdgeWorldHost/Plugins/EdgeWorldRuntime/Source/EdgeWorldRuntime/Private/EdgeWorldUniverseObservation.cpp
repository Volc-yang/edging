#include "EdgeWorldUniverseObservation.h"
#include "Misc/Crc.h"
#if PLATFORM_MAC
#include <CommonCrypto/CommonDigest.h>
#endif

namespace EdgeUniverse
{
// FString's default equality/hash fold case, and C-string comparisons stop at NUL.
// Protocol strings and decoded JSON keys instead compare every counted UTF16 unit.
static bool SameText(const FString& A, const FString& B)
{
 return A.Len() == B.Len() && (A.IsEmpty() || FMemory::Memcmp(*A, *B, SIZE_T(A.Len()) * sizeof(TCHAR)) == 0);
}
static uint32 TextHash(const FString& S)
{
 return FCrc::MemCrc32(*S, S.Len() * int32(sizeof(TCHAR)));
}
template<typename T> struct FTextMapKeys : TDefaultMapKeyFuncs<FString, T, false>
{
 static bool Matches(const FString& A, const FString& B) { return SameText(A, B); }
 static uint32 GetKeyHash(const FString& Key) { return TextHash(Key); }
};
template<typename T> using TextMap = TMap<FString, T, FDefaultSetAllocator, FTextMapKeys<T>>;
struct FTextSetKeys : DefaultKeyFuncs<FString, false>
{
 static bool Matches(const FString& A, const FString& B) { return SameText(A, B); }
 static uint32 GetKeyHash(const FString& Key) { return TextHash(Key); }
};
using TextSet = TSet<FString, FTextSetKeys>;
static bool HasText(const TArray<FString>& Values, const FString& Wanted)
{
 return Values.ContainsByPredicate([&](const FString& S) { return SameText(S, Wanted); });
}
static void AppendUnit(FString& S, TCHAR C)
{
 // FString::AppendChar silently drops zero; decoded JSON must retain it.
 int32 N = S.Len(); auto& Data = S.GetCharArray(); Data.SetNumUninitialized(N + 2);
 Data[N] = C; Data[N + 1] = 0;
}
static FString TextSlice(const FString& S, int32 Start, int32 Count)
{
 FString Result; Result.GetCharArray().Append(*S + Start, Count); Result.GetCharArray().Add(0); return Result;
}
static TArray<FString> SplitUnits(const FString& S, TCHAR Delimiter, bool CullEmpty = true)
{
 TArray<FString> Result; int32 Start = 0;
 for (int32 I = 0; I <= S.Len(); ++I)
 {
  if (I == S.Len() || S[I] == Delimiter)
  {
   if (!CullEmpty || I > Start) Result.Add(TextSlice(S, Start, I - Start));
   Start = I + 1;
  }
 }
 return Result;
}
static bool StartsText(const FString& S, const FString& Prefix)
{
 return S.Len() >= Prefix.Len() && SameText(TextSlice(S, 0, Prefix.Len()), Prefix);
}
static bool EndsText(const FString& S, const FString& Suffix)
{
 return S.Len() >= Suffix.Len() && SameText(TextSlice(S, S.Len() - Suffix.Len(), Suffix.Len()), Suffix);
}
static bool HasSubText(const FString& S, const FString& Needle)
{
 for (int32 I = 0; I + Needle.Len() <= S.Len(); ++I)
  if (SameText(TextSlice(S, I, Needle.Len()), Needle)) return true;
 return false;
}
constexpr int64 MaxInt = 9007199254740991LL;
struct FValue;
using V = TSharedPtr<FValue>;
struct FValue
{
 enum EType { Null, Bool, Int, String, Array, Object } Type = Null;
 bool B = false; int64 I = 0; FString S; TArray<V> A; TextMap<V> O;
};
static V Make(FValue::EType Type) { V X = MakeShared<FValue>(); X->Type = Type; return X; }
static bool Is(const V& X, FValue::EType T) { return X && X->Type == T; }
static V Get(const V& X, const FString& Key) { if (!Is(X,FValue::Object)) return {}; const V* P=X->O.Find(Key); return P ? *P : V(); }
static FString Str(const V& X) { return Is(X,FValue::String) ? X->S : FString(); }
static int64 Num(const V& X) { return Is(X,FValue::Int) ? X->I : -MaxInt; }
static V Body(const V& R) { return Get(R,TEXT("body")); }
static V Refs(const V& R) { return Get(R,TEXT("refs")); }
static FString Kind(const V& R) { return Str(Get(R,TEXT("kind"))); }
static bool Eq(const V& A, const V& B);
static int32 Hex(uint32 C) { return C>='0'&&C<='9'?C-'0':C>='a'&&C<='f'?C-'a'+10:C>='A'&&C<='F'?C-'A'+10:-1; }
static bool LowerHex(const FString& S,int32 N) { if(S.Len()!=N)return false; for(TCHAR C:S)if(!(C>='0'&&C<='9')&&!(C>='a'&&C<='f'))return false; return true; }
static bool Id(const FString& S) { if(S.IsEmpty()||S.Len()>64||S[0]<'a'||S[0]>'z')return false; for(TCHAR C:S)if(!(C>='a'&&C<='z')&&!(C>='0'&&C<='9')&&C!='.'&&C!='_'&&C!='-')return false; return true; }
static void Scalar(FString& S,uint32 C) { if(C>0xffff){C-=0x10000;AppendUnit(S,TCHAR(0xd800+(C>>10)));AppendUnit(S,TCHAR(0xdc00+(C&1023)));}else AppendUnit(S,TCHAR(C)); }
static uint32 NextScalar(const FString& S,int32& I) { uint32 C=uint32(S[I++]); if(C>=0xd800&&C<=0xdbff&&I<S.Len())C=0x10000+((C-0xd800)<<10)+(uint32(S[I++])-0xdc00); return C; }
static int32 ScalarCount(const FString& S) { int32 I = 0, N = 0; while (I < S.Len()) { NextScalar(S, I); ++N; } return N; }

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
 case FValue::Object:{TArray<FString> Keys;for(const auto& Pair:X->O)Keys.Add(Pair.Key);Keys.Sort(OrdinalLess);FString S=TEXT("{");for(int32 I=0;I<Keys.Num();++I){if(I)S+=TEXT(",");S+=Quote(Keys[I])+TEXT(":")+Canon(X->O[Keys[I]]);}return S+TEXT("}");}}
 return {};
}
static bool Eq(const V& A,const V& B){return A&&B&&SameText(Canon(A),Canon(B));}
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
 FString Error; V Schema; TextMap<V> Records; TextSet Needed, Membership;
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
  if(SameText(S,TEXT("id")))return Identity(X);if(SameText(S,TEXT("hash")))return Hash(X);if(SameText(S,TEXT("nullable_hash")))return Is(X,FValue::Null)||Hash(X);
  if(SameText(S,TEXT("uint")))return Uint(X);if(SameText(S,TEXT("sint")))return Require(Is(X,FValue::Int),TEXT("INTEGER"));
  if(SameText(S,TEXT("f64"))){double D;return Require(F64(X,D),TEXT("F64"));}
  if(SameText(S,TEXT("nullable_mm")))return Require(Is(X,FValue::Null)||(Is(X,FValue::Int)&&FMath::Abs(X->I)<=1000),TEXT("PHYSICS_INVALID"));
  if(SameText(S,TEXT("delta"))||SameText(S,TEXT("steps"))||SameText(S,TEXT("blob_size")))return Uint(X)&&Require(SameText(S,TEXT("delta"))?X->I<=1:SameText(S,TEXT("steps"))?X->I<=256:X->I>0&&X->I<=8388608,TEXT("LIMIT"));
  if(SameText(S,TEXT("nullable_case")))return Require(Is(X,FValue::Null)||SameText(Str(X),TEXT("weak"))||SameText(Str(X),TEXT("strong")),TEXT("SCHEMA"));
  if(SameText(S,TEXT("class")))return Require(SameText(Str(X),TEXT("synthetic-contract-only"))||SameText(Str(X),TEXT("genesis-runtime")),TEXT("PROFILE"));
  if(SameText(S,TEXT("media")))return Require(SameText(Str(X),TEXT("application/x-edgeworld-static-vector"))||SameText(Str(X),TEXT("application/x-genesis-gstraj;version=1.4.3")),TEXT("PROFILE"));
  if(SameText(S,TEXT("output")))return Require(Is(X,FValue::String)&&ScalarCount(X->S)<=1024,TEXT("SCHEMA"));
  if(SameText(S,TEXT("json_object")))return Require(Is(X,FValue::Object),TEXT("SCHEMA"));
  if(SameText(S,TEXT("i7_config")))return Require(Eq(X,Get(Schema,TEXT("physics_parameters"))),TEXT("PROFILE"));
  if(SameText(S,TEXT("signs")))return Require(SameText(Canon(X),TEXT("[1,-1,1]")),TEXT("SCHEMA"));
  if(SameText(S,TEXT("vec3")))return Vec(X,3,TNumericLimits<double>::Max());
  if(SameText(S,TEXT("extent")))return IntVec(X,4)&&Require(Num(X->A[0])<Num(X->A[2])&&Num(X->A[1])<Num(X->A[3]),TEXT("GEOGRAPHY"));
  if(SameText(S,TEXT("polygon"))||SameText(S,TEXT("polyline")))
  {
   if(!Require(Is(X,FValue::Array)&&X->A.Num()>=(SameText(S,TEXT("polygon"))?4:2),TEXT("GEOGRAPHY")))return false;
   for(const V& P:X->A)if(!IntVec(P,2))return false;
   return Require(!SameText(S,TEXT("polygon"))||Eq(X->A[0],X->A.Last()),TEXT("GEOGRAPHY"));
  }
  if(SameText(S,TEXT("ids"))){if(!Require(Is(X,FValue::Array)&&X->A.Num()>=2&&X->A.Num()<=6,TEXT("GEOGRAPHY")))return false;TextSet Seen;for(const V& C:X->A){if(!Identity(C)||!Require(!Seen.Contains(C->S),TEXT("ID")))return false;Seen.Add(C->S);}return true;}
  if(SameText(S,TEXT("assets"))||SameText(S,TEXT("decorations"))||SameText(S,TEXT("sources"))||SameText(S,TEXT("dependencies"))||SameText(S,TEXT("bindings"))||SameText(S,TEXT("bodies"))||SameText(S,TEXT("contacts")))return Entries(X,S);
  TArray<FString> Values;S.ParseIntoArray(Values,TEXT("|"));return Require(Is(X,FValue::String)&&HasText(Values,X->S),TEXT("SCHEMA"));
 }
 bool Entries(const V& X,const FString& K)
 {
  int32 Limit=SameText(K,TEXT("assets"))?64:SameText(K,TEXT("decorations"))?1000:SameText(K,TEXT("sources"))?32:SameText(K,TEXT("dependencies"))?16:SameText(K,TEXT("contacts"))?32:2;
  if(!Require(Is(X,FValue::Array)&&X->A.Num()<=Limit,TEXT("LIMIT")))return false;
  TextSet Seen;FString Last;int64 Total=0;int32 Index=0;
  for(const V& Item:X->A)
  {
   FString IdentityValue;
   if(SameText(K,TEXT("assets")))
   {
    if(!Keys(Item,TEXT("asset_id,uri,content_sha256,byte_count,source,use,license_status,dependencies"))||!Identity(Get(Item,TEXT("asset_id")))||!Hash(Get(Item,TEXT("content_sha256")))||!Uint(Get(Item,TEXT("byte_count"))))return false;
    IdentityValue=Str(Get(Item,TEXT("asset_id")));Total+=Num(Get(Item,TEXT("byte_count")));
    FString Uri=Str(Get(Item,TEXT("uri")));TArray<FString> UriParts=SplitUnits(Uri,TCHAR('.'),false);FString Path=UriParts[0],Name=UriParts.Num()==2?UriParts[1]:FString();
    if(!Require(StartsText(Uri,TEXT("/Engine/"))&&UriParts.Num()==2&&!Name.IsEmpty(),TEXT("ASSET")))return false;
    auto AssetChar=[](TCHAR C){return (C>='A'&&C<='Z')||(C>='a'&&C<='z')||(C>='0'&&C<='9')||C=='_';};
    for(TCHAR C:Path)if(!Require(C=='/'||AssetChar(C),TEXT("ASSET")))return false;for(TCHAR C:Name)if(!Require(AssetChar(C),TEXT("ASSET")))return false;
    if(!Require(SameText(Str(Get(Item,TEXT("source"))),TEXT("installed-ue-5.8.3-basicshapes"))&&SameText(Str(Get(Item,TEXT("use"))),TEXT("technical-proxy-not-realism"))&&SameText(Str(Get(Item,TEXT("license_status"))),TEXT("ue-installed-content-no-shipping-review")),TEXT("ASSET")))return false;
    V Deps=Get(Item,TEXT("dependencies"));if(!Require(Is(Deps,FValue::Array),TEXT("ASSET")))return false;TextSet Ds;for(const V& D:Deps->A){if(!Identity(D)||!Require(!Ds.Contains(D->S),TEXT("ASSET")))return false;Ds.Add(D->S);}
    if(!Require((Last.IsEmpty()||OrdinalLess(Last,IdentityValue))&&Total<=2147483648LL,TEXT("ASSET")))return false;Last=IdentityValue;
   }
   else if(SameText(K,TEXT("decorations")))
   {
    if(!Keys(Item,TEXT("instance_id,place_id,asset_id,position_cm,scale_milli")))return false;
    for(const TCHAR* Key:{TEXT("instance_id"),TEXT("place_id"),TEXT("asset_id")})if(!Identity(Get(Item,Key)))return false;
    if(!IntVec(Get(Item,TEXT("position_cm")),3)||!IntVec(Get(Item,TEXT("scale_milli")),3))return false;
    for(const V& N:Get(Item,TEXT("scale_milli"))->A)if(!Require(N->I>0,TEXT("SCHEMA")))return false;IdentityValue=Str(Get(Item,TEXT("instance_id")));
   }
   else if(SameText(K,TEXT("sources")))
   {
    if(!Keys(Item,TEXT("path,sha256"))||!Hash(Get(Item,TEXT("sha256"))))return false;IdentityValue=Str(Get(Item,TEXT("path")));TArray<FString> Parts=SplitUnits(IdentityValue,TCHAR('/'),false);
    if(!Require(Is(Get(Item,TEXT("path")),FValue::String)&&!StartsText(IdentityValue,TEXT("/"))&&!HasText(Parts,TEXT("..")),TEXT("BUILD")))return false;
   }
   else if(SameText(K,TEXT("dependencies")))
   {
    if(!Keys(Item,TEXT("name,version,metadata_sha256"))||!Hash(Get(Item,TEXT("metadata_sha256")))||!Require(Is(Get(Item,TEXT("name")),FValue::String)&&Is(Get(Item,TEXT("version")),FValue::String),TEXT("BUILD")))return false;IdentityValue=Str(Get(Item,TEXT("name")));
   }
   else if(SameText(K,TEXT("bindings")))
   {
    if(!Keys(Item,TEXT("physical_id,existence_id,genesis_name,role,config_entity_index")))return false;for(const TCHAR* Key:{TEXT("physical_id"),TEXT("existence_id"),TEXT("genesis_name")})if(!Identity(Get(Item,Key)))return false;
    if(!Uint(Get(Item,TEXT("config_entity_index")))||!Require(SameText(Str(Get(Item,TEXT("role"))),TEXT("dynamic"))||SameText(Str(Get(Item,TEXT("role"))),TEXT("support")),TEXT("PHYSICS_INVALID")))return false;IdentityValue=Str(Get(Item,TEXT("physical_id")));
   }
   else if(SameText(K,TEXT("bodies")))
   {
    if(!Keys(Item,TEXT("physical_id,position_m,quaternion_wxyz,linear_velocity_m_s,angular_velocity_rad_s,mass_kg"))||!Identity(Get(Item,TEXT("physical_id"))))return false;
    if(!Vec(Get(Item,TEXT("position_m")),3,10)||!Vec(Get(Item,TEXT("quaternion_wxyz")),4,1.001)||!Vec(Get(Item,TEXT("linear_velocity_m_s")),3,100)||!Vec(Get(Item,TEXT("angular_velocity_rad_s")),3,100))return false;
    double Norm=0,Mass;for(const V& C:Get(Item,TEXT("quaternion_wxyz"))->A){double D;F64(C,D);Norm+=D*D;}
    IdentityValue=Str(Get(Item,TEXT("physical_id")));
    // Frozen fixed-support identity admits either zero sign; preserve original bits.
    const bool bSupport=SameText(IdentityValue,TEXT("body-support"));
    if(!Require((bSupport||SameText(IdentityValue,TEXT("body-dynamic")))&&FMath::Abs(Norm-1)<=1e-4&&F64(Get(Item,TEXT("mass_kg")),Mass)&&(bSupport?Mass>=0:Mass>0),TEXT("PHYSICS_INVALID")))return false;
   }
   else
   {
    if(!Keys(Item,TEXT("pair,position_m,force_on_dynamic_n"))||!Require(SameText(Canon(Get(Item,TEXT("pair"))),TEXT("[\"body-dynamic\",\"body-support\"]")),TEXT("PHYSICS_INVALID"))||!Vec(Get(Item,TEXT("position_m")),3,10)||!Vec(Get(Item,TEXT("force_on_dynamic_n")),3,1e6))return false;
    // Same fixed pair for every contact, then lexical f64 bit-vector ordering.
    FString Order=Canon(Get(Item,TEXT("position_m")))+Canon(Get(Item,TEXT("force_on_dynamic_n")));
    if(!Require(Last.IsEmpty()||!OrdinalLess(Order,Last),TEXT("PHYSICS_INVALID")))return false;Last=Order;
   }
   if(!SameText(K,TEXT("contacts"))){if(!Require(!Seen.Contains(IdentityValue),TEXT("ID")))return false;Seen.Add(IdentityValue);}
   if(SameText(K,TEXT("bindings"))||SameText(K,TEXT("bodies")))if(!Require(SameText(IdentityValue,(Index==0?TEXT("body-dynamic"):TEXT("body-support"))),TEXT("PHYSICS_INVALID")))return false;++Index;
  }
  return Require((!SameText(K,TEXT("bindings"))&&!SameText(K,TEXT("bodies")))||Index==2,TEXT("PHYSICS_INVALID"));
 }
 V ExpectedRefs(const V& R)
 {
  FString K=Kind(R);V Shape=Make(FValue::Object);V Base=Get(Get(Schema,TEXT("refs")),K);if(!Base)return {};
  if(SameText(K,TEXT("route"))){V Ids=Get(Body(R),TEXT("place_ids"));if(!Is(Ids,FValue::Array))return {};for(int32 I=0;I<Ids->A.Num();++I){V S=Make(FValue::String);S->S=TEXT("place");Shape->O.Add(FString::Printf(TEXT("p%d"),I),S);}return Shape;}
  for(const auto& P:Base->O){FString Key=P.Key;Key.RemoveFromEnd(TEXT("?"),ESearchCase::CaseSensitive);if(SameText(K,TEXT("manifest"))&&Num(Get(Body(R),TEXT("revision")))==0&&!SameText(Key,TEXT("state")))continue;if(SameText(K,TEXT("event"))&&SameText(Key,TEXT("prior_event"))&&!Get(Refs(R),TEXT("prior_event")))continue;Shape->O.Add(Key,P.Value);}return Shape;
 }
 bool Record(const V& R)
 {
  if(!Tree(R)||!Keys(R,TEXT("domain,version,world_id,kind,id,body,refs"))||!Require(SameText(Str(Get(R,TEXT("domain"))),TEXT("edgeworld.universe.authority"))&&SameText(Str(Get(R,TEXT("version"))),TEXT("0.2")),TEXT("DOMAIN"))||!Identity(Get(R,TEXT("world_id")))||!Identity(Get(R,TEXT("id"))))return false;
  FString K=Kind(R);V Shape=Get(Get(Schema,TEXT("body")),K);if(!Require(!!Shape,TEXT("SCHEMA"))||!Exact(Body(R),Shape))return false;
  for(const auto& P:Shape->O)if(!Field(Get(Body(R),P.Key),Str(P.Value)))return false;
  if(!Exact(Refs(R),ExpectedRefs(R)))return false;for(const auto& P:Refs(R)->O)if(!Hash(P.Value))return false;
  return Require(Canon(R).Len()<=Num(Get(Get(Schema,TEXT("kind_bytes")),K)),TEXT("LIMIT"));
 }
 V Target(const V& R,const FString& Key){const V* P=Records.Find(Str(Get(Refs(R),Key)));if(!P){Require(false,TEXT("PROOF"));return {};}return *P;}
 bool SameRef(const V& A,const FString& AK,const V& B,const FString& BK){return Eq(Get(Refs(A),AK),Get(Refs(B),BK));}
 bool Static(const V& R,const FEdgeWorldUniverseContext& C);
 bool Transition(const V& M);
 bool Verify(const V& Env,const FEdgeWorldUniverseExpectation& E,FEdgeWorldUniverseObservation& Out);
};
bool FValidator::Static(const V& R,const FEdgeWorldUniverseContext& C)
{
 V B=Body(R);FString K=Kind(R);auto T=[&](const FString& Key){return Target(R,Key);};
 if(Get(B,TEXT("artifact_class"))&&!Require(SameText(Str(Get(B,TEXT("artifact_class"))),C.ArtifactClass),TEXT("PROFILE")))return false;
 if(SameText(K,TEXT("existence")))return Require(Eq(Get(R,TEXT("id")),Get(B,TEXT("existence_id"))),TEXT("ID"));
 if(SameText(K,TEXT("unit_transform"))){double D;return Require(F64(Get(B,TEXT("scale")),D)&&D==100,TEXT("PHYSICS_INVALID"));}
 if(SameText(K,TEXT("provider_build")))return Require(SameText(Sha(Canon(R),true),C.ExpectedBuild)&&(!SameText(C.ArtifactClass,TEXT("genesis-runtime"))||!Is(Get(B,TEXT("adapter_source_sha256")),FValue::Null)),TEXT("BUILD"));
 if(SameText(K,TEXT("resolved_options")))
 {
  bool Runtime=SameText(C.ArtifactClass,TEXT("genesis-runtime"));if(!Require(SameText(Sha(Canon(R),true),C.ExpectedOptions)&&SameText(Str(Get(Refs(R),TEXT("build"))),C.ExpectedBuild)&&SameText(Str(Get(B,TEXT("resolution"))),(Runtime?TEXT("runtime-exported"):TEXT("static-declared"))),TEXT("BUILD")))return false;
  if(!Runtime&&!Require(Get(B,TEXT("exports"))->O.IsEmpty(),TEXT("BUILD")))return false;
  if(Runtime){V Ex=Get(B,TEXT("exports"));if(!Keys(Ex,TEXT("sim_options,rigid_options,dynamic_morph,support_morph,rigid_material")))return false;for(const auto& P:Ex->O)if(!Require(Is(P.Value,FValue::Object)&&P.Value->O.Num()>0,TEXT("BUILD")))return false;}return true;
 }
 if(SameText(K,TEXT("physics_config")))return Require(SameText(Str(Get(Refs(R),TEXT("build"))),C.ExpectedBuild)&&SameText(Str(Get(Refs(R),TEXT("options"))),C.ExpectedOptions)&&SameRef(T(TEXT("options")),TEXT("build"),R,TEXT("build"))&&SameText(Str(Get(Body(T(TEXT("options"))),TEXT("parameter_hash"))),Sha(Canon(Get(B,TEXT("config"))))),TEXT("BUILD"));
 if(SameText(K,TEXT("physics_binding")))
 {
  V Entities=Get(Get(Body(T(TEXT("config"))),TEXT("config")),TEXT("entities"));V Bindings=Get(B,TEXT("bindings"));if(!Require(Is(Entities,FValue::Array)&&Entities->A.Num()==2,TEXT("PHYSICS_INVALID")))return false;
  for(int32 I=0;I<2;++I){V Entry=Bindings->A[I],Entity=Entities->A[I];for(const TCHAR* Key:{TEXT("physical_id"),TEXT("existence_id"),TEXT("genesis_name")})if(!Require(Eq(Get(Entry,Key),Get(Entity,Key)),TEXT("PHYSICS_INVALID")))return false;
   if(!Require(Num(Get(Entry,TEXT("config_entity_index")))==I&&SameText(Str(Get(Entry,TEXT("role"))),(I==0?TEXT("dynamic"):TEXT("support"))),TEXT("PHYSICS_INVALID")))return false;
   V Exists=Body(T(I==0?TEXT("dynamic_exists"):TEXT("support_exists")));if(!Require(Eq(Get(Exists,TEXT("existence_id")),Get(Entry,TEXT("existence_id")))&&SameText(Str(Get(Exists,TEXT("category"))),TEXT("physical")),TEXT("REFERENCE")))return false;
  }return true;
 }
 if(SameText(K,TEXT("physics_sample"))||SameText(K,TEXT("checkpoint_descriptor"))||SameText(K,TEXT("physics_snapshot")))
 {
  if(!Require(SameRef(T(TEXT("binding")),TEXT("config"),R,TEXT("config")),TEXT("PHYSICS_INVALID")))return false;
  if(SameText(K,TEXT("checkpoint_descriptor")))
  {
   bool Syn=SameText(C.ArtifactClass,TEXT("synthetic-contract-only"));return Require(SameText(Str(Get(B,TEXT("format"))),(Syn?TEXT("synthetic-static-bytes"):TEXT("genesis-gstraj")))&&SameText(Str(Get(B,TEXT("media_type"))),(Syn?TEXT("application/x-edgeworld-static-vector"):TEXT("application/x-genesis-gstraj;version=1.4.3")))&&SameRef(R,TEXT("build"),T(TEXT("config")),TEXT("build")),TEXT("PROFILE"));
  }
  if(SameText(K,TEXT("physics_snapshot"))){for(const TCHAR* Name:{TEXT("sample"),TEXT("checkpoint")})if(!Require(SameRef(T(Name),TEXT("config"),R,TEXT("config"))&&SameRef(T(Name),TEXT("binding"),R,TEXT("binding")),TEXT("PHYSICS_INVALID")))return false;return Require((SameText(Str(Get(B,TEXT("case_id"))),TEXT("initial")))==(Num(Get(B,TEXT("physical_step_count")))==0),TEXT("PHYSICS_INVALID"));}
  return true;
 }
 if(SameText(K,TEXT("place")))return Require(SameText(Str(Get(Body(T(TEXT("existence"))),TEXT("category"))),TEXT("place")),TEXT("REFERENCE"));
 if(SameText(K,TEXT("route"))){V Ids=Get(B,TEXT("place_ids"));for(int32 I=0;I<Ids->A.Num();++I)if(!Require(Eq(Get(Body(T(FString::Printf(TEXT("p%d"),I))),TEXT("place_id")),Ids->A[I]),TEXT("GEOGRAPHY")))return false;return true;}
 if(SameText(K,TEXT("watercourse")))return Require(SameText(Str(Get(Body(T(TEXT("upstream"))),TEXT("place_kind"))),TEXT("forest"))&&SameText(Str(Get(Body(T(TEXT("marsh"))),TEXT("place_kind"))),TEXT("river_marsh"))&&SameText(Str(Get(Body(T(TEXT("outlet"))),TEXT("place_kind"))),TEXT("ocean")),TEXT("GEOGRAPHY"));
 if(SameText(K,TEXT("asset_manifest")))
 {
  V EntriesValue=Get(B,TEXT("entries"));TextMap<V> Assets;for(const V& A:EntriesValue->A)Assets.Add(Str(Get(A,TEXT("asset_id"))),A);
  TextSet Active,Done;TFunction<bool(const FString&)> Visit=[&](const FString& Name){if(!Require(Assets.Contains(Name)&&!Active.Contains(Name),TEXT("ASSET")))return false;if(Done.Contains(Name))return true;Active.Add(Name);for(const V& D:Get(Assets[Name],TEXT("dependencies"))->A)if(!Visit(D->S))return false;Active.Remove(Name);Done.Add(Name);return true;};
  for(const auto& A:Assets)if(!Visit(A.Key))return false;
  return Require(SameText(Str(Get(B,TEXT("dependency_status"))),(SameText(C.ArtifactClass,TEXT("synthetic-contract-only"))?TEXT("declared-static"):TEXT("runtime-resolved"))),TEXT("ASSET"));
 }
 if(SameText(K,TEXT("projection")))
 {
  TextSet Assets;for(const V& A:Get(Body(T(TEXT("assets"))),TEXT("entries"))->A)Assets.Add(Str(Get(A,TEXT("asset_id"))));
  for(const V& D:Get(B,TEXT("decorations"))->A)if(!Require(Assets.Contains(Str(Get(D,TEXT("asset_id")))),TEXT("ASSET")))return false;return true;
 }
 if(SameText(K,TEXT("world_manifest")))
 {
  if(!Require(SameText(Str(Get(Body(T(TEXT("world_existence"))),TEXT("category"))),TEXT("world")),TEXT("GEOGRAPHY")))return false;
  TextSet Places,Exists;for(const TCHAR* Key:{TEXT("world_existence"),TEXT("dynamic_existence"),TEXT("support_existence")})Exists.Add(Str(Get(Body(T(Key)),TEXT("existence_id"))));
  V Bounds=Get(B,TEXT("extent_cm"));auto InBounds=[&](const V& Points){for(const V& P:Points->A)if(!Require(Num(P->A[0])>=Num(Bounds->A[0])&&Num(P->A[0])<=Num(Bounds->A[2])&&Num(P->A[1])>=Num(Bounds->A[1])&&Num(P->A[1])<=Num(Bounds->A[3]),TEXT("GEOGRAPHY")))return false;return true;};
  for(const TCHAR* Name:{TEXT("city"),TEXT("wildland"),TEXT("plain"),TEXT("forest"),TEXT("river_marsh"),TEXT("ocean")})
  {
   V P=T(Name);if(!Require(SameText(Str(Get(Body(P),TEXT("place_kind"))),Name),TEXT("GEOGRAPHY")))return false;
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
 if(SameText(K,TEXT("state")))
 {
  V World=T(TEXT("world")),Binding=Target(T(TEXT("snapshot")),TEXT("binding"));return Require(SameRef(Binding,TEXT("dynamic_exists"),World,TEXT("dynamic_existence"))&&SameRef(Binding,TEXT("support_exists"),World,TEXT("support_existence")),TEXT("REFERENCE"));
 }
 if(SameText(K,TEXT("intent")))
 {
  bool Retain=SameText(Str(Get(B,TEXT("action"))),TEXT("retain_snapshot"));return Require(Retain?(Num(Get(B,TEXT("tick_delta")))==0&&Is(Get(B,TEXT("case_id")),FValue::Null)&&Num(Get(B,TEXT("budget")))==0):(Num(Get(B,TEXT("tick_delta")))==1&&(SameText(Str(Get(B,TEXT("case_id"))),TEXT("weak"))||SameText(Str(Get(B,TEXT("case_id"))),TEXT("strong")))),TEXT("TRANSITION"));
 }
 return true;
}
bool FValidator::Transition(const V& M)
{
 V S=Target(M,TEXT("state")),B=Body(M),SB=Body(S),Snap=Target(S,TEXT("snapshot"));
 if(!Require(Eq(Get(B,TEXT("tick")),Get(SB,TEXT("tick")))&&Eq(Get(B,TEXT("revision")),Get(SB,TEXT("revision")))&&Eq(Get(B,TEXT("watermark")),Get(SB,TEXT("revision"))),TEXT("WATERMARK")))return false;
 if(Num(Get(B,TEXT("revision")))==0)return Require(Num(Get(B,TEXT("tick")))==0&&Is(Get(SB,TEXT("development_mm")),FValue::Null)&&Num(Get(SB,TEXT("random_cursor")))==0&&Num(Get(SB,TEXT("budget")))==8&&SameText(Str(Get(Body(Snap),TEXT("case_id"))),TEXT("initial"))&&Num(Get(Body(Snap),TEXT("physical_step_count")))==0,TEXT("HEAD"));
 V Prior=Target(M,TEXT("prior_manifest")),Previous=Target(Prior,TEXT("state")),PB=Body(Previous),Event=Target(M,TEXT("event")),Index=Target(M,TEXT("index")),Result=Target(Index,TEXT("result")),Admission=Target(Event,TEXT("admission")),Command=Target(Admission,TEXT("command")),Candidate=Target(Admission,TEXT("candidate")),Intent=Target(Command,TEXT("intent")),IB=Body(Intent),Approval=Target(Command,TEXT("approval")),Proposal=Target(Command,TEXT("proposal")),CB=Body(Candidate),Before=Target(Previous,TEXT("snapshot"));
 if(!Error.IsEmpty())return false;
 if(!Require(Num(Get(B,TEXT("revision")))==Num(Get(Body(Prior),TEXT("revision")))+1&&SameRef(S,TEXT("world"),Previous,TEXT("world"))&&SameRef(Event,TEXT("state"),M,TEXT("state"))&&SameRef(Result,TEXT("state"),M,TEXT("state"))&&SameRef(Result,TEXT("event"),M,TEXT("event")),TEXT("HEAD")))return false;
 V PriorEvent=Get(Refs(Prior),TEXT("event")),EventPrior=Get(Refs(Event),TEXT("prior_event"));
 if(!Require((!PriorEvent&&!EventPrior)||Eq(PriorEvent,EventPrior),TEXT("HEAD")))return false;
 if(!Require(SameRef(Candidate,TEXT("prior_state"),Prior,TEXT("state"))&&SameRef(Candidate,TEXT("command"),Admission,TEXT("command"))&&SameRef(Result,TEXT("command"),Admission,TEXT("command"))&&SameRef(Candidate,TEXT("snapshot"),S,TEXT("snapshot"))&&SameRef(Result,TEXT("checkpoint"),S,TEXT("snapshot")),TEXT("REFERENCE")))return false;
 FString Principal=Str(Get(IB,TEXT("principal")));
 if(!Require(SameRef(Approval,TEXT("proposal"),Command,TEXT("proposal"))&&SameRef(Approval,TEXT("intent"),Command,TEXT("intent"))&&SameText(Str(Get(Body(Proposal),TEXT("principal"))),Principal)&&SameText(Str(Get(Body(Approval),TEXT("principal"))),Principal)&&SameText(Str(Get(Body(Admission),TEXT("principal"))),Principal),TEXT("AUTHORIZATION")))return false;
 if(!Require(Num(Get(IB,TEXT("expected_revision")))==Num(Get(PB,TEXT("revision")))&&Eq(Get(IB,TEXT("expected_revision")),Get(Body(Admission),TEXT("evaluated_revision")))&&Eq(Get(IB,TEXT("random_cursor")),Get(PB,TEXT("random_cursor")))&&Num(Get(IB,TEXT("expected_revision")))<=Num(Get(Body(Approval),TEXT("expires_revision"))),TEXT("AUTHORIZATION")))return false;
 if(!Require(Eq(Get(CB,TEXT("revision")),Get(SB,TEXT("revision")))&&Eq(Get(CB,TEXT("tick")),Get(SB,TEXT("tick")))&&Eq(Get(CB,TEXT("influence_mm")),Get(SB,TEXT("development_mm"))),TEXT("TRANSITION")))return false;
 for(const TCHAR* Key:{TEXT("config"),TEXT("binding")})if(!Require(SameRef(Intent,Key,Snap,Key)&&SameRef(Before,Key,Snap,Key),TEXT("PHYSICS_INVALID")))return false;
 if(SameText(Str(Get(IB,TEXT("action"))),TEXT("retain_snapshot")))
 {
  if(!Require(Num(Get(IB,TEXT("tick_delta")))==0&&Is(Get(IB,TEXT("case_id")),FValue::Null)&&Num(Get(IB,TEXT("budget")))==0&&SameText(Str(Get(CB,TEXT("adapter_kind"))),TEXT("checkpoint_reuse"))&&SameRef(Previous,TEXT("snapshot"),S,TEXT("snapshot")),TEXT("TRANSITION")))return false;
  for(const TCHAR* Key:{TEXT("tick"),TEXT("development_mm"),TEXT("budget"),TEXT("random_cursor")})if(!Require(Eq(Get(SB,Key),Get(PB,Key)),TEXT("TRANSITION")))return false;
 }
 else
 {
  V OldSample=Target(Before,TEXT("sample")),NewSample=Target(Snap,TEXT("sample"));double Dummy;uint64 OldBits=0,NewBits=0;
  V OldBodies=Get(Body(OldSample),TEXT("bodies")),NewBodies=Get(Body(NewSample),TEXT("bodies"));
  if(!Require(Is(OldBodies,FValue::Array)&&Is(NewBodies,FValue::Array)&&OldBodies->A.Num()==2&&NewBodies->A.Num()==2,TEXT("PHYSICS_INVALID")))return false;
  F64(Get(OldBodies->A[0],TEXT("position_m"))->A[2],Dummy,&OldBits);F64(Get(NewBodies->A[0],TEXT("position_m"))->A[2],Dummy,&NewBits);int64 D=0;
  if(!Require(Influence(OldBits,NewBits,D)&&Num(Get(SB,TEXT("development_mm")))==D&&Num(Get(IB,TEXT("tick_delta")))==1&&(SameText(Str(Get(IB,TEXT("case_id"))),TEXT("weak"))||SameText(Str(Get(IB,TEXT("case_id"))),TEXT("strong")))&&SameText(Str(Get(CB,TEXT("adapter_kind"))),TEXT("genesis"))&&Num(Get(SB,TEXT("tick")))==Num(Get(PB,TEXT("tick")))+1&&Eq(Get(Body(Snap),TEXT("case_id")),Get(IB,TEXT("case_id")))&&Num(Get(Body(Snap),TEXT("physical_step_count")))==Num(Get(Body(Before),TEXT("physical_step_count")))+8&&Num(Get(SB,TEXT("budget")))==Num(Get(PB,TEXT("budget")))-Num(Get(IB,TEXT("budget")))&&Num(Get(SB,TEXT("random_cursor")))==Num(Get(PB,TEXT("random_cursor")))+1,TEXT("TRANSITION")))return false;
 }
 V RB=Body(Result);if(!Require(Eq(Get(RB,TEXT("command_id")),Get(IB,TEXT("command_id")))&&Eq(Get(RB,TEXT("tick")),Get(SB,TEXT("tick")))&&Eq(Get(RB,TEXT("revision")),Get(SB,TEXT("revision")))&&Eq(Get(RB,TEXT("watermark")),Get(SB,TEXT("revision"))),TEXT("WATERMARK")))return false;
 return Require(Eq(Get(Body(Index),TEXT("command_id")),Get(IB,TEXT("command_id")))&&Eq(Get(Body(Index),TEXT("fingerprint")),Get(Refs(Result),TEXT("command"))),TEXT("COMMAND_CONFLICT"));
}
static FVector3d Vector(const V& X){double D[3]={};for(int32 I=0;I<3;++I)F64(X->A[I],D[I]);return FVector3d(D[0],D[1],D[2]);}
static TArray<FEdgeWorldUniverseBody> Bodies(const V& Sample)
{
 TArray<FEdgeWorldUniverseBody> Result;for(const V& X:Get(Body(Sample),TEXT("bodies"))->A){FEdgeWorldUniverseBody B;B.PhysicalId=Str(Get(X,TEXT("physical_id")));B.PositionM=Vector(Get(X,TEXT("position_m")));B.LinearVelocityMS=Vector(Get(X,TEXT("linear_velocity_m_s")));B.AngularVelocityRadS=Vector(Get(X,TEXT("angular_velocity_rad_s")));V Q=Get(X,TEXT("quaternion_wxyz"));double D[4]={};for(int32 I=0;I<4;++I)F64(Q->A[I],D[I]);B.QuaternionWXYZ=FVector4d(D[0],D[1],D[2],D[3]);F64(Get(X,TEXT("mass_kg")),B.MassKg);Result.Add(B);}return Result;
}
static bool SameContext(const FEdgeWorldUniverseContext& A,const FEdgeWorldUniverseContext& B){return SameText(A.WorldId,B.WorldId)&&SameText(A.AuthorityRoot,B.AuthorityRoot)&&SameText(A.TrustAlgorithm,B.TrustAlgorithm)&&SameText(A.TrustAnchor,B.TrustAnchor)&&SameText(A.ArtifactClass,B.ArtifactClass)&&SameText(A.ExpectedBuild,B.ExpectedBuild)&&SameText(A.ExpectedOptions,B.ExpectedOptions);}
static bool CanonicalRoot(const FString& Root){if(!StartsText(Root,TEXT("/"))||StartsText(Root,TEXT("//"))||(Root.Len()>1&&EndsText(Root,TEXT("/")))||HasSubText(Root,TEXT("//")))return false;TArray<FString> P=SplitUnits(Root,TCHAR('/'));for(TCHAR C:Root)if(C==0)return false;return !HasText(P,TEXT("."))&&!HasText(P,TEXT(".."));}
bool FValidator::Verify(const V& Env,const FEdgeWorldUniverseExpectation& E,FEdgeWorldUniverseObservation& Out)
{
 const auto& C=E.Context;const auto& H=E.TrustedHead;
 if(!Require(CanonicalRoot(C.AuthorityRoot)&&SameText(C.AuthorityRoot,H.Context.AuthorityRoot),TEXT("ROOT_MISMATCH"))||!Require(SameContext(C,H.Context),TEXT("AUTHORIZATION")))return false;
 if(!Require(Id(C.WorldId)&&Id(E.RequestId)&&LowerHex(C.TrustAnchor,64)&&LowerHex(C.ExpectedBuild,64)&&LowerHex(C.ExpectedOptions,64)&&LowerHex(H.Head,64)&&SameText(C.TrustAlgorithm,TEXT("local-hmac-sha256.v0.2"))&&SameText(H.Domain,TEXT("edgeworld.universe.authority"))&&SameText(H.Version,TEXT("0.2"))&&SameText(H.Profile,TEXT("composite-rigid-support.v0.2"))&&(SameText(H.StorageState,TEXT("ready"))||SameText(H.StorageState,TEXT("unconfirmed_readonly")))&&SameText(C.ArtifactClass,(E.bFixtureOnly?TEXT("synthetic-contract-only"):TEXT("genesis-runtime"))),TEXT("PROFILE")))return false;
 if(!Require(E.Tick>=0&&E.Tick<=MaxInt&&E.Revision>=0&&E.Revision<=MaxInt&&E.Watermark==E.Revision,TEXT("WATERMARK")))return false;
 if(!Keys(Env,TEXT("protocol_version,request_id,ok,result"))||!Require(Num(Get(Env,TEXT("protocol_version")))==1&&Is(Get(Env,TEXT("ok")),FValue::Bool)&&Get(Env,TEXT("ok"))->B,TEXT("SCHEMA"))||!Require(SameText(Str(Get(Env,TEXT("request_id"))),E.RequestId),TEXT("PROOF")))return false;
 V R=Get(Env,TEXT("result"));if(!Keys(R,TEXT("domain,version,world_id,operation,payload"))||!Require(SameText(Str(Get(R,TEXT("domain"))),H.Domain)&&SameText(Str(Get(R,TEXT("version"))),H.Version),TEXT("DOMAIN"))||!Require(SameText(Str(Get(R,TEXT("world_id"))),C.WorldId)&&SameText(Str(Get(R,TEXT("operation"))),TEXT("observe")),TEXT("WORLD")))return false;
 V P=Get(R,TEXT("payload"));if(!Keys(P,TEXT("manifest,state,event,watermark,storage_state,artifact_class,head,membership,records,opaque_refs"))||!Require(SameText(Str(Get(P,TEXT("storage_state"))),H.StorageState)&&SameText(Str(Get(P,TEXT("artifact_class"))),C.ArtifactClass)&&SameText(Str(Get(P,TEXT("head"))),H.Head),TEXT("PROOF"))||!Require(Num(Get(P,TEXT("watermark")))==E.Watermark,TEXT("WATERMARK")))return false;
 V Ms=Get(P,TEXT("membership")),Aux=Get(P,TEXT("records")),Opaque=Get(P,TEXT("opaque_refs")),M=Get(P,TEXT("manifest")),S=Get(P,TEXT("state")),Event=Get(P,TEXT("event"));
 if(!Require(Is(Ms,FValue::Array)&&Ms->A.Num()>=1&&Ms->A.Num()<=64&&Is(Aux,FValue::Array)&&Aux->A.Num()<=96&&Is(Opaque,FValue::Array)&&Opaque->A.Num()<=256,TEXT("PROOF_LIMIT")))return false;
 TArray<V> All=Ms->A;All.Append(Aux->A);All.Add(M);All.Add(S);if(!Is(Event,FValue::Null))All.Add(Event);
 TextMap<FString> Identities;TextMap<int32> Counts;
 for(const V& X:All)
 {
  if(!Record(X)||!Require(SameText(Str(Get(X,TEXT("world_id"))),C.WorldId),TEXT("WORLD")))return false;
  FString D=Sha(Canon(X),true),IdentityKey=Kind(X)+TEXT(":")+Str(Get(X,TEXT("id")));if(!Require(!D.IsEmpty(),TEXT("HASH")))return false;
  if(!Require(!Identities.Contains(IdentityKey)||SameText(Identities[IdentityKey],D),TEXT("ID")))return false;Identities.Add(IdentityKey,D);Records.Add(D,X);Counts.FindOrAdd(Kind(X))++;
 }
 for(const auto& Pair:Records)
 {
  V ER=ExpectedRefs(Pair.Value);for(const auto& Ref:Refs(Pair.Value)->O){const V* T=Records.Find(Ref.Value->S);if(T&&!Require(SameText(Kind(*T),Str(Get(ER,Ref.Key))),TEXT("PROOF")))return false;}
 }
 for(const auto& Cnt:Counts)if(!Require(Cnt.Value<=Num(Get(Get(Schema,TEXT("proof_kind_max")),Cnt.Key)),TEXT("PROOF_LIMIT")))return false;
 FString Selected=Sha(Canon(M),true);TextSet Explicit;Explicit.Add(Selected);Explicit.Add(Sha(Canon(S),true));if(!Is(Event,FValue::Null))Explicit.Add(Sha(Canon(Event),true));
 for(const V& X:Ms->A){FString D=Sha(Canon(X),true);if(!Require(SameText(Kind(X),TEXT("manifest"))&&!Membership.Contains(D),TEXT("PROOF")))return false;Membership.Add(D);Explicit.Add(D);}
 TextSet AuxSet;for(const V& X:Aux->A){FString D=Sha(Canon(X),true);if(!Require(!AuxSet.Contains(D)&&!Explicit.Contains(D),TEXT("PROOF")))return false;AuxSet.Add(D);}
 if(!Require(SameText(Sha(Canon(Ms->A[0]),true),H.Head)&&SameText(Sha(Canon(Ms->A.Last()),true),Selected),TEXT("PROOF")))return false;
 for(int32 I=0;I<Ms->A.Num();++I){V A=Ms->A[I];if(!Require(Eq(Get(Body(A),TEXT("watermark")),Get(Body(A),TEXT("revision"))),TEXT("WATERMARK")))return false;if(I+1==Ms->A.Num())break;V B=Ms->A[I+1];int64 Delta=Num(Get(Body(A),TEXT("tick")))-Num(Get(Body(B),TEXT("tick")));if(!Require(SameText(Str(Get(Refs(A),TEXT("prior_manifest"))),Sha(Canon(B),true))&&Num(Get(Body(A),TEXT("revision")))==Num(Get(Body(B),TEXT("revision")))+1&&(Delta==0||Delta==1),TEXT("PROOF")))return false;}
 if(!Require(SameText(Kind(M),TEXT("manifest"))&&SameText(Kind(S),TEXT("state"))&&Num(Get(Body(M),TEXT("tick")))==E.Tick&&Num(Get(Body(M),TEXT("revision")))==E.Revision&&Num(Get(Body(M),TEXT("watermark")))==E.Watermark&&SameText(Str(Get(Refs(M),TEXT("state"))),Sha(Canon(S),true)),TEXT("WATERMARK")))return false;
 if(!Require((E.Revision==0&&Is(Event,FValue::Null))||(E.Revision>0&&SameText(Kind(Event),TEXT("event"))&&SameText(Str(Get(Refs(M),TEXT("event"))),Sha(Canon(Event),true))),TEXT("PROOF")))return false;
 FString Previous=Str(Get(Refs(M),TEXT("prior_manifest")));TextSet Active,Done;
 TFunction<bool(const FString&,bool)> Expand=[&](const FString& D,bool Prev)
 {
  FString Memo=D+(Prev?TEXT(":p"):TEXT(":n"));if(!Require(Records.Contains(D)&&!Active.Contains(Memo),TEXT("PROOF")))return false;if(Done.Contains(Memo))return true;Active.Add(Memo);Needed.Add(D);V X=Records[D];
  for(const auto& Ref:Refs(X)->O){if(SameText(Kind(X),TEXT("manifest"))&&(SameText(Ref.Key,TEXT("prior_manifest"))||(Prev&&!SameText(Ref.Key,TEXT("state")))))continue;if(SameText(Kind(X),TEXT("event"))&&SameText(Ref.Key,TEXT("prior_event")))continue;if(!Expand(Ref.Value->S,false))return false;}
  Active.Remove(Memo);Done.Add(Memo);return true;
 };
 if(!Expand(Selected,false)||(!Previous.IsEmpty()&&!Expand(Previous,true)))return false;
 for(const auto& X:Records)if(!Require(Needed.Contains(X.Key)||Membership.Contains(X.Key),TEXT("PROOF")))return false;
 TextSet Omitted;
 for(const auto& X:Records)
 {
  for(const auto& Ref:Refs(X.Value)->O)if(!Records.Contains(Ref.Value->S))
  {
   bool Allowed=(SameText(Kind(X.Value),TEXT("event"))&&SameText(Ref.Key,TEXT("prior_event")))||(SameText(Kind(X.Value),TEXT("manifest"))&&!SameText(X.Key,Selected)&&!SameText(Ref.Key,TEXT("state")))||(SameText(Kind(X.Value),TEXT("manifest"))&&Membership.Contains(X.Key)&&!SameText(X.Key,Selected)&&!SameText(X.Key,Previous));
   if(!Require(Allowed,TEXT("PROOF")))return false;Omitted.Add(Ref.Value->S);
  }
 }
 TArray<FString> Sorted=Omitted.Array();Sorted.Sort(OrdinalLess);if(!Require(Sorted.Num()==Opaque->A.Num(),TEXT("PROOF")))return false;for(int32 I=0;I<Sorted.Num();++I)if(!Require(SameText(Str(Opaque->A[I]),Sorted[I]),TEXT("PROOF")))return false;
 // Membership-only ancestors are not renderable dependencies. Never validate them by expanding opaque history.
 for(const FString& D:Needed){V X=Records[D];if(SameText(Kind(X),TEXT("event"))||SameText(Kind(X),TEXT("candidate"))||SameText(Kind(X),TEXT("command"))||SameText(Kind(X),TEXT("approval"))||SameText(Kind(X),TEXT("admission"))||SameText(Kind(X),TEXT("result"))||SameText(Kind(X),TEXT("index"))||SameText(Kind(X),TEXT("manifest")))continue;if(!Static(X,C))return false;}
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
 if(!Previous.IsEmpty()){V PS=Target(Records[Previous],TEXT("state"));Out.PriorSelection=FInt64Point(Num(Get(Body(PS),TEXT("tick"))),Num(Get(Body(PS),TEXT("revision"))));Out.PriorBodies=Bodies(Target(Target(PS,TEXT("snapshot")),TEXT("sample")));}
 Sorted=Needed.Array();Sorted.Sort(OrdinalLess);for(const FString& D:Sorted){V X=Records[D];FEdgeWorldUniverseRecord ROut;ROut.Digest=D;ROut.Kind=Kind(X);ROut.Id=Str(Get(X,TEXT("id")));ROut.CanonicalJson=Canon(X);Out.SelectedRecords.Add(ROut);}return Error.IsEmpty();
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

namespace EdgeUniverse
{
static V String(const FString& S){V X=Make(FValue::String);X->S=S;return X;}
static V Integer(int64 N){V X=Make(FValue::Int);X->I=N;return X;}
static V ParseText(const FString& S){FTCHARToUTF8 U(*S);FReader R(MakeArrayView(reinterpret_cast<const uint8*>(U.Get()),U.Length()));return R.Parse(false);}
static bool ValidContext(const FEdgeWorldUniverseContext& C,bool Fixture)
{
 return Id(C.WorldId)&&CanonicalRoot(C.AuthorityRoot)&&LowerHex(C.TrustAnchor,64)&&LowerHex(C.ExpectedBuild,64)&&LowerHex(C.ExpectedOptions,64)
  &&SameText(C.TrustAlgorithm,TEXT("local-hmac-sha256.v0.2"))&&SameText(C.ArtifactClass,Fixture?TEXT("synthetic-contract-only"):TEXT("genesis-runtime"));
}
static FEdgeWorldUniverseContext Context(const V& X)
{
 FEdgeWorldUniverseContext C;C.WorldId=Str(Get(X,TEXT("world_id")));C.AuthorityRoot=Str(Get(X,TEXT("authority_root")));C.TrustAlgorithm=Str(Get(X,TEXT("trust_algorithm")));C.TrustAnchor=Str(Get(X,TEXT("trust_anchor")));C.ArtifactClass=Str(Get(X,TEXT("artifact_class")));C.ExpectedBuild=Str(Get(X,TEXT("expected_build")));C.ExpectedOptions=Str(Get(X,TEXT("expected_options")));return C;
}
static bool Head(FValidator& Vld,const V& X,const FEdgeWorldUniverseContext& Expected,FEdgeWorldUniverseHeadBinding& Out)
{
 if(!Vld.Keys(X,TEXT("domain,version,profile,world_id,authority_root,trust_algorithm,trust_anchor,artifact_class,expected_build,expected_options,head,storage_state")))return false;
 Out.Context=Context(X);Out.Domain=Str(Get(X,TEXT("domain")));Out.Version=Str(Get(X,TEXT("version")));Out.Profile=Str(Get(X,TEXT("profile")));Out.Head=Str(Get(X,TEXT("head")));Out.StorageState=Str(Get(X,TEXT("storage_state")));
 return Vld.Require(SameContext(Expected,Out.Context)&&SameText(Out.Domain,TEXT("edgeworld.universe.authority"))&&SameText(Out.Version,TEXT("0.2"))&&SameText(Out.Profile,TEXT("composite-rigid-support.v0.2"))&&LowerHex(Out.Head,64)&&(SameText(Out.StorageState,TEXT("ready"))||SameText(Out.StorageState,TEXT("unconfirmed_readonly"))),TEXT("AUTHORIZATION"));
}
static bool SameRecord(FValidator& Vld,const V& R,const FString& K,const FString& World)
{return Vld.Record(R)&&Vld.Require(SameText(Kind(R),K)&&SameText(Str(Get(R,TEXT("world_id"))),World),TEXT("DOMAIN"));}
static bool ResultRecord(FValidator& Vld,const V& R,const FString& World,const FString& Command)
{
 return SameRecord(Vld,R,TEXT("result"),World)
  &&Vld.Require(SameText(Str(Get(Refs(R),TEXT("command"))),Command),TEXT("REFERENCE"))
  &&Vld.Require(Eq(Get(Body(R),TEXT("watermark")),Get(Body(R),TEXT("revision")))
    &&Num(Get(Body(R),TEXT("tick")))<=Num(Get(Body(R),TEXT("revision"))),TEXT("WATERMARK"));
}

}

bool FEdgeWorldUniverseControlParser::PublicPins(TArrayView<const uint8> Raw,const FString& Hash,FEdgeWorldUniversePublicPins& Out,FString& Error,bool Fixture)
{
 using namespace EdgeUniverse;Out={};Error.Reset();FReader Reader(Raw);V X=Reader.Parse(false);FValidator Vld;
 auto Fail=[&](){Error=Reader.Error.IsEmpty()?(Vld.Error.IsEmpty()?TEXT("PUBLIC_PINS"):Vld.Error):Reader.Error;return false;};
 if(!X||Raw.Num()>16384||!Vld.Keys(X,TEXT("domain,version,profile,world_id,authority_root,trust_algorithm,trust_anchor,artifact_class,expected_build,expected_options,principal,allowed_actions")))return Fail();
 FString Text=Canon(X);FTCHARToUTF8 U(*Text);
 if(!Vld.Require(U.Length()==Raw.Num()&&FMemory::Memcmp(U.Get(),Raw.GetData(),Raw.Num())==0&&LowerHex(Hash,64)&&SameText(Sha(Text),Hash),TEXT("CANONICAL")))return Fail();
 FEdgeWorldUniversePublicPins Candidate;Candidate.Context=Context(X);Candidate.Principal=Str(Get(X,TEXT("principal")));V A=Get(X,TEXT("allowed_actions"));
 if(!Vld.Require(ValidContext(Candidate.Context,Fixture)&&Id(Candidate.Principal)&&SameText(Str(Get(X,TEXT("domain"))),TEXT("edgeworld.universe.authority"))&&SameText(Str(Get(X,TEXT("version"))),TEXT("0.2"))&&SameText(Str(Get(X,TEXT("profile"))),TEXT("composite-rigid-support.v0.2"))&&Is(A,FValue::Array)&&A->A.Num()<=2,TEXT("PROFILE")))return Fail();
 for(const V& Item:A->A){FString S=Str(Item);if(!Vld.Require((SameText(S,TEXT("physics_step"))||SameText(S,TEXT("retain_snapshot")))&&!HasText(Candidate.AllowedActions,S),TEXT("AUTHORIZATION")))return Fail();Candidate.AllowedActions.Add(S);}
 Out=MoveTemp(Candidate);return true;
}

bool FEdgeWorldUniverseControlParser::Verify(TArrayView<const uint8> Raw,const FEdgeWorldUniverseControlExpectation& E,FEdgeWorldUniverseControl& Out,FString& Error)
{
 using namespace EdgeUniverse;Out={};Error.Reset();FReader Reader(Raw);V Env=Reader.Parse(true);FValidator Vld;FEdgeWorldUniverseControl C;
 auto Fail=[&](){Error=Reader.Error.IsEmpty()?(Vld.Error.IsEmpty()?TEXT("CONTROL"):Vld.Error):Reader.Error;return false;};
 if(!Env||!Vld.Require(ValidContext(E.Pins.Context,E.bFixtureOnly)&&Id(E.RequestId)&&Id(E.Pins.Principal),TEXT("PROFILE")))return Fail();
 V OK=Get(Env,TEXT("ok"));if(!Vld.Require(Is(OK,FValue::Bool)&&Num(Get(Env,TEXT("protocol_version")))==1&&SameText(Str(Get(Env,TEXT("request_id"))),E.RequestId),TEXT("PROOF")))return Fail();
 if(!OK->B)
 {
  V Err=Get(Env,TEXT("error"));if(!Vld.Keys(Env,TEXT("protocol_version,request_id,ok,error"))||!Vld.Keys(Err,TEXT("code,message,commit_status")))return Fail();
  C.ErrorCode=Str(Get(Err,TEXT("code")));C.CommitStatus=Str(Get(Err,TEXT("commit_status")));
  if(!Vld.Require(!C.ErrorCode.IsEmpty()&&C.ErrorCode.Len()<=64&&Is(Get(Err,TEXT("message")),FValue::String)&&(SameText(C.CommitStatus,TEXT("not_attempted"))||SameText(C.CommitStatus,TEXT("unknown"))||SameText(C.CommitStatus,TEXT("confirmed"))),TEXT("SCHEMA")))return Fail();
  for(TCHAR Ch:C.ErrorCode)if(!Vld.Require((Ch>='A'&&Ch<='Z')||(Ch>='0'&&Ch<='9')||Ch=='_',TEXT("SCHEMA")))return Fail();
  Out=MoveTemp(C);return true;
 }
 V R=Get(Env,TEXT("result"));if(!Vld.Keys(Env,TEXT("protocol_version,request_id,ok,result"))||!Vld.Keys(R,TEXT("domain,version,world_id,operation,payload")))return Fail();
 if(!Vld.Require(SameText(Str(Get(R,TEXT("domain"))),TEXT("edgeworld.universe.authority"))&&SameText(Str(Get(R,TEXT("version"))),TEXT("0.2"))&&SameText(Str(Get(R,TEXT("world_id"))),E.Pins.Context.WorldId)&&SameText(Str(Get(R,TEXT("operation"))),E.Operation),TEXT("DOMAIN")))return Fail();
 V P=Get(R,TEXT("payload"));if(!Head(Vld,Get(P,TEXT("head_binding")),E.Pins.Context,C.Head))return Fail();
 if(SameText(E.Operation,TEXT("status")))
 {
  if(!Vld.Keys(P,TEXT("world_id,head,tick,revision,watermark,state,event,storage_state,artifact_class,head_binding"))||!Vld.Uint(Get(P,TEXT("tick")))||!Vld.Uint(Get(P,TEXT("revision")))||!Vld.Uint(Get(P,TEXT("watermark")))||!Vld.Hash(Get(P,TEXT("state"))))return Fail();
  C.Tick=Num(Get(P,TEXT("tick")));C.Revision=Num(Get(P,TEXT("revision")));C.Watermark=Num(Get(P,TEXT("watermark")));C.State=Str(Get(P,TEXT("state")));C.Event=Str(Get(P,TEXT("event")));
  if(!Vld.Require(C.Tick<=C.Revision&&C.Watermark==C.Revision&&SameText(Str(Get(P,TEXT("world_id"))),E.Pins.Context.WorldId)&&SameText(Str(Get(P,TEXT("head"))),C.Head.Head)&&SameText(Str(Get(P,TEXT("storage_state"))),C.Head.StorageState)&&SameText(Str(Get(P,TEXT("artifact_class"))),E.Pins.Context.ArtifactClass)&&((C.Revision==0&&Is(Get(P,TEXT("event")),FValue::Null))||(C.Revision>0&&LowerHex(C.Event,64))),TEXT("WATERMARK")))return Fail();
 }
 else if(SameText(E.Operation,TEXT("prepare")))
 {
  if(!Vld.Keys(P,TEXT("command_records,command_digest,committed_result,head_binding")))return Fail();V A=Get(P,TEXT("command_records"));
  if(!Vld.Require(Is(A,FValue::Array)&&A->A.Num()==4,TEXT("SCHEMA")))return Fail();
  const TCHAR* Kinds[]={TEXT("proposal"),TEXT("intent"),TEXT("approval"),TEXT("command")};for(int32 I=0;I<4;++I)if(!SameRecord(Vld,A->A[I],Kinds[I],E.Pins.Context.WorldId))return Fail();
  V Proposal=A->A[0],Intent=A->A[1],Approval=A->A[2],Command=A->A[3];FString PH=Sha(Canon(Proposal),true),IH=Sha(Canon(Intent),true),AH=Sha(Canon(Approval),true),CH=Sha(Canon(Command),true);
  if(!Vld.Require(Eq(Proposal,ParseText(E.ProposalJson))&&Eq(Intent,ParseText(E.IntentJson))&&SameText(Str(Get(Approval,TEXT("id"))),E.ApprovalId)&&SameText(Str(Get(Body(Approval),TEXT("receipt_id"))),E.ApprovalId)&&SameText(Str(Get(Command,TEXT("id"))),E.CommandRecordId)&&SameText(Str(Get(Body(Approval),TEXT("principal"))),E.Pins.Principal)&&SameText(Str(Get(Body(Intent),TEXT("principal"))),E.Pins.Principal)&&SameText(Str(Get(Body(Proposal),TEXT("principal"))),E.Pins.Principal)&&Eq(Get(Body(Approval),TEXT("expires_revision")),Get(Body(Intent),TEXT("expected_revision"))),TEXT("AUTHORIZATION")))return Fail();
  V AR=Refs(Approval),CR=Refs(Command);
  if(!Vld.Require(SameText(Str(Get(AR,TEXT("proposal"))),PH)&&SameText(Str(Get(AR,TEXT("intent"))),IH)&&SameText(Str(Get(CR,TEXT("proposal"))),PH)&&SameText(Str(Get(CR,TEXT("intent"))),IH)&&SameText(Str(Get(CR,TEXT("approval"))),AH)&&SameText(Str(Get(P,TEXT("command_digest"))),CH),TEXT("REFERENCE")))return Fail();
  C.CommandRecordsJson=Canon(A);C.CommandDigest=CH;V Committed=Get(P,TEXT("committed_result"));
  if(!Is(Committed,FValue::Null))
  {
   if(!ResultRecord(Vld,Committed,E.Pins.Context.WorldId,CH)||!Vld.Require(SameText(Str(Get(Refs(Committed),TEXT("command"))),CH)&&Eq(Get(Body(Committed),TEXT("command_id")),Get(Body(Intent),TEXT("command_id"))),TEXT("REFERENCE")))return Fail();C.CommittedResultJson=Canon(Committed);
  }
 }
 else if(SameText(E.Operation,TEXT("advance"))||SameText(E.Operation,TEXT("initialize")))
 {
  if(!Vld.Keys(P,TEXT("manifest,result,commit_status,head_binding"))||!Vld.Hash(Get(P,TEXT("manifest")))||!Vld.Require(SameText(Str(Get(P,TEXT("commit_status"))),TEXT("confirmed")),TEXT("SCHEMA")))return Fail();
  C.Manifest=Str(Get(P,TEXT("manifest")));C.CommitStatus=TEXT("confirmed");V Result=Get(P,TEXT("result"));
  if(SameText(E.Operation,TEXT("initialize"))){if(!Vld.Require(Is(Result,FValue::Null),TEXT("SCHEMA")))return Fail();}
  else {if(!ResultRecord(Vld,Result,E.Pins.Context.WorldId,E.CommandDigest)||!Vld.Require(LowerHex(E.CommandDigest,64)&&SameText(Str(Get(Refs(Result),TEXT("command"))),E.CommandDigest)&&Eq(Get(Body(Result),TEXT("revision")),Get(Body(Result),TEXT("watermark"))),TEXT("REFERENCE")))return Fail();C.CommittedResultJson=Canon(Result);}
 }
 else {Vld.Require(false,TEXT("OPERATION"));return Fail();}
 C.bSuccess=true;Out=MoveTemp(C);return true;
}

bool FEdgeWorldUniverseControlParser::Request(const FString& Op,const FString& RequestId,const FString& PayloadJson,FString& Out,FString& Error)
{
 using namespace EdgeUniverse;Out.Reset();Error.Reset();FValidator Vld;V P=ParseText(PayloadJson);
 const TCHAR* Keys=SameText(Op,TEXT("status"))?TEXT("domain,version,world_id"):SameText(Op,TEXT("observe"))?TEXT("domain,version,world_id,tick,revision,watermark"):SameText(Op,TEXT("initialize"))?TEXT("domain,version,world_id,test_profile"):SameText(Op,TEXT("prepare"))?TEXT("domain,version,world_id,principal,proposal,intent,approval_id,command_record_id"):SameText(Op,TEXT("advance"))?TEXT("domain,version,world_id,principal,command_records,command_digest"):nullptr;
 const bool bBase=Keys&&Id(RequestId)&&Vld.Keys(P,Keys)
  &&SameText(Str(Get(P,TEXT("domain"))),TEXT("edgeworld.universe.authority"))
  &&SameText(Str(Get(P,TEXT("version"))),TEXT("0.2"))&&Id(Str(Get(P,TEXT("world_id"))));
 if(!bBase){Error=TEXT("REQUEST");return false;}
 if(SameText(Op,TEXT("observe")))
 {
  if(!Vld.Uint(Get(P,TEXT("tick")))||!Vld.Uint(Get(P,TEXT("revision")))||!Vld.Uint(Get(P,TEXT("watermark")))
   ||!Vld.Require(Eq(Get(P,TEXT("revision")),Get(P,TEXT("watermark"))),TEXT("WATERMARK"))){Error=Vld.Error;return false;}
 }
 if(SameText(Op,TEXT("initialize"))&&!SameText(Str(Get(P,TEXT("test_profile"))),TEXT("composite-rigid-support.v0.2"))){Error=TEXT("PROFILE");return false;}
 if((SameText(Op,TEXT("prepare"))||SameText(Op,TEXT("advance")))&&!Vld.Identity(Get(P,TEXT("principal")))){Error=Vld.Error;return false;}
 if(SameText(Op,TEXT("prepare")))
 {
  if(!Vld.Record(Get(P,TEXT("proposal")))||!Vld.Record(Get(P,TEXT("intent")))
   ||!Vld.Identity(Get(P,TEXT("approval_id")))||!Vld.Identity(Get(P,TEXT("command_record_id")))){Error=Vld.Error;return false;}
 }
 if(SameText(Op,TEXT("advance")))
 {
  V A=Get(P,TEXT("command_records"));if(!Vld.Require(Is(A,FValue::Array)&&A->A.Num()==4,TEXT("SCHEMA"))||!Vld.Hash(Get(P,TEXT("command_digest")))){Error=Vld.Error;return false;}
  for(const V& Item:A->A)if(!Vld.Record(Item)){Error=Vld.Error;return false;}
 }

 V Env=Make(FValue::Object);Env->O.Add(TEXT("protocol_version"),Integer(1));Env->O.Add(TEXT("request_id"),String(RequestId));Env->O.Add(TEXT("operation"),String(Op));Env->O.Add(TEXT("payload"),P);FString Text=Canon(Env);if(Text.Len()>1048576){Error=TEXT("LIMIT");return false;}Out=Text+TEXT("\n");return true;
}

bool FEdgeWorldUniverseControlParser::BuildPrepare(const FEdgeWorldUniversePublicPins& Pins,const FEdgeWorldUniverseObservation& Current,const FString& CommandId,const FString& Action,const FString& Case,FString& OutPayload,FString& OutProposal,FString& OutIntent,FString& Error)
{
 using namespace EdgeUniverse;OutPayload.Reset();OutProposal.Reset();OutIntent.Reset();Error.Reset();bool Physical=SameText(Action,TEXT("physics_step"));
 if(!Id(CommandId)||CommandId.Len()>40||!HasText(Pins.AllowedActions,Action)||(!Physical&&!SameText(Action,TEXT("retain_snapshot")))||(Physical&&!SameText(Case,TEXT("weak"))&&!SameText(Case,TEXT("strong")))||!SameText(Current.WorldId,Pins.Context.WorldId)||Current.StorageState!=TEXT("ready")||Current.Revision>=MaxInt||Current.RandomCursor>=MaxInt||(Physical&&(Current.Tick>=MaxInt||Current.PhysicalStepCount>=256||Current.Budget<1))){Error=TEXT("NOT_READY");return false;}
 auto Record=[&](const FString& K,const FString& IdValue,const V& B,const V& R){V X=Make(FValue::Object);X->O.Add(TEXT("domain"),String(TEXT("edgeworld.universe.authority")));X->O.Add(TEXT("version"),String(TEXT("0.2")));X->O.Add(TEXT("world_id"),String(Pins.Context.WorldId));X->O.Add(TEXT("kind"),String(K));X->O.Add(TEXT("id"),String(IdValue));X->O.Add(TEXT("body"),B);X->O.Add(TEXT("refs"),R);return X;};
 V PB=Make(FValue::Object);PB->O.Add(TEXT("principal"),String(Pins.Principal));PB->O.Add(TEXT("output"),String(TEXT("explicit UE technical ")+Action));V Proposal=Record(TEXT("proposal"),TEXT("proposal-")+CommandId,PB,Make(FValue::Object));
 V IB=Make(FValue::Object);IB->O.Add(TEXT("principal"),String(Pins.Principal));IB->O.Add(TEXT("command_id"),String(CommandId));IB->O.Add(TEXT("expected_revision"),Integer(Current.Revision));IB->O.Add(TEXT("random_cursor"),Integer(Current.RandomCursor));IB->O.Add(TEXT("budget"),Integer(Physical?1:0));IB->O.Add(TEXT("tick_delta"),Integer(Physical?1:0));IB->O.Add(TEXT("action"),String(Action));IB->O.Add(TEXT("case_id"),Physical?String(Case):Make(FValue::Null));V IR=Make(FValue::Object);IR->O.Add(TEXT("config"),String(Current.Config));IR->O.Add(TEXT("binding"),String(Current.Binding));V Intent=Record(TEXT("intent"),TEXT("intent-")+CommandId,IB,IR);
 FValidator Vld;if(!Vld.Record(Proposal)||!Vld.Record(Intent)){Error=Vld.Error;return false;}
 V P=Make(FValue::Object);P->O.Add(TEXT("domain"),String(TEXT("edgeworld.universe.authority")));P->O.Add(TEXT("version"),String(TEXT("0.2")));P->O.Add(TEXT("world_id"),String(Pins.Context.WorldId));P->O.Add(TEXT("principal"),String(Pins.Principal));P->O.Add(TEXT("proposal"),Proposal);P->O.Add(TEXT("intent"),Intent);P->O.Add(TEXT("approval_id"),String(TEXT("approval-")+CommandId));P->O.Add(TEXT("command_record_id"),String(TEXT("record-")+CommandId));OutPayload=Canon(P);OutProposal=Canon(Proposal);OutIntent=Canon(Intent);return true;
}

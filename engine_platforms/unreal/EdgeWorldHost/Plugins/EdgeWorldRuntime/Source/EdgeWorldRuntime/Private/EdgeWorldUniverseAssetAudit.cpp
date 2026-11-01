#include "EdgeWorldUniverseAssetAudit.h"
#if WITH_EDITOR
#include "EdgeWorldUniverseObservation.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/FileManager.h"
#include "Misc/EngineVersion.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/PackageFileSummary.h"
#include "UObject/PackageTrailer.h"
#include "UObject/UObjectGlobals.h"
#if PLATFORM_MAC
#include <CommonCrypto/CommonDigest.h>
#endif

namespace UniverseAssetAudit
{
using J = TSharedPtr<FJsonObject>;
static J Object() { return MakeShared<FJsonObject>(); }
static bool Same(const FString& A, const FString& B)
{
 return A.Len() == B.Len() && (!A.Len() || FMemory::Memcmp(*A, *B, A.Len() * sizeof(TCHAR)) == 0);
}
static bool Less(const FString& A, const FString& B)
{
 // All admitted content URIs/IDs are ASCII. Audit descriptions are not identity keys.
 int32 N = FMath::Min(A.Len(), B.Len());
 for (int32 I = 0; I < N; ++I) if (A[I] != B[I]) return A[I] < B[I];
 return A.Len() < B.Len();
}
static bool Prefix(const FString& S, const FString& P)
{
 return S.Len() >= P.Len() && FMemory::Memcmp(*S, *P, P.Len() * sizeof(TCHAR)) == 0;
}
static bool Identifier(const FString& S)
{
 if (S.IsEmpty() || S.Len() > 64 || S[0] < 'a' || S[0] > 'z') return false;
 for (TCHAR C : S) if (!(C >= 'a' && C <= 'z') && !(C >= '0' && C <= '9') && C != '-' && C != '_' && C != '.') return false;
 return true;
}
static bool AssetUri(const FString& S)
{
 if (!Prefix(S, TEXT("/Engine/"))) return false;
 int32 Dot = INDEX_NONE;
 for (int32 I = 0; I < S.Len(); ++I)
 {
  TCHAR C = S[I];
  if (C == '.') { if (Dot != INDEX_NONE) return false; Dot = I; continue; }
  bool NameChar = (C >= 'A' && C <= 'Z') || (C >= 'a' && C <= 'z') || (C >= '0' && C <= '9') || C == '_';
  if (!NameChar && !(C == '/' && Dot == INDEX_NONE)) return false;
 }
 return Dot > 8 && Dot + 1 < S.Len();
}
static FString Json(const J& Value)
{
 FString Out;
 auto Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
 FJsonSerializer::Serialize(Value.ToSharedRef(), Writer);
 return Out;
}
static TSharedPtr<FJsonValue> String(const FString& S) { return MakeShared<FJsonValueString>(S); }
static TArray<TSharedPtr<FJsonValue>> Strings(const TArray<FString>& Values)
{
 TArray<TSharedPtr<FJsonValue>> Out;
 for (const FString& S : Values) Out.Add(String(S));
 return Out;
}
static FString AsciiSha(const FString& S)
{
#if PLATFORM_MAC
 FTCHARToUTF8 Bytes(*S); uint8 Hash[CC_SHA256_DIGEST_LENGTH];
 if (!CC_SHA256(Bytes.Get(), static_cast<CC_LONG>(Bytes.Length()), Hash)) return {};
 return BytesToHex(Hash, CC_SHA256_DIGEST_LENGTH).ToLower();
#else
 return {};
#endif
}
struct FNode
{
 FName Package;
 FString Uri, Id, PrimaryFile, Sha;
 int64 PrimaryBytes = 0;
 TArray<FName> Dependencies;
 J Audit = Object();
};
class FCollector
{
 IAssetRegistry& Registry;
 TArray<FNode> Nodes;
 TArray<FName> Seen, Native;
 TArray<J> Edges, Gaps, Files;
 int64 BytesRead = 0;
 int64 UniqueFileBytes = 0;
 TArray<FString> FileNames;
 TArray<FFileStatData> FileStats;
 bool bStopped = false;
 double Start = FPlatformTime::Seconds();
 static constexpr int32 MaxNodes = 64, MaxEdges = 4096, MaxFiles = 1024;
 static constexpr int64 MaxBytes = 2147483648LL;
 const FString EngineContent = FPaths::ConvertRelativePathToFull(FPaths::EngineContentDir());
 const TCHAR* Roots[4] = { TEXT("/Engine/BasicShapes/Cube.Cube"), TEXT("/Engine/BasicShapes/Cylinder.Cylinder"), TEXT("/Engine/BasicShapes/Sphere.Sphere"), TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial") };
 const TCHAR* RootIds[4] = { TEXT("asset-cube"), TEXT("asset-cylinder"), TEXT("asset-sphere"), TEXT("asset-material") };
public:
 explicit FCollector(IAssetRegistry& R) : Registry(R) {}
 void Gap(const TCHAR* Code, const FString& Subject)
 {
  if (Gaps.Num() >= 256) { bStopped = true; return; }
  J G = Object(); G->SetStringField(TEXT("code"), Code); G->SetStringField(TEXT("subject"), Subject); Gaps.Add(G);
 }
 bool Budget()
 {
  if (FPlatformTime::Seconds() - Start <= 90 && !bStopped) return true;
  if (!bStopped) Gap(TEXT("EXPORT_TIME_LIMIT"), TEXT("90 seconds internal collection limit"));
  bStopped = true; return false;
 }
 bool HashFile(const FString& Filename, FString& Hash, int64& Count)
 {
  if (!Budget()) return false;
  if (FileNames.ContainsByPredicate([&](const FString& P) { return Same(P, Filename); }))
  { Gap(TEXT("AMBIGUOUS_SHARED_FILE"), Filename); return false; }
  if (FPlatformFileManager::Get().GetPlatformFile().IsSymlink(*Filename) != ESymlinkResult::NonSymlink)
  { Gap(TEXT("SYMLINK_OR_UNKNOWN_FILE_KIND"), Filename); return false; }
  FFileStatData Before = IFileManager::Get().GetStatData(*Filename);
  if (!Before.bIsValid || Before.bIsDirectory || Before.FileSize <= 0)
  { Gap(TEXT("MISSING_OR_INVALID_FILE"), Filename); return false; }
  if (Files.Num() >= MaxFiles || Before.FileSize > MaxBytes - UniqueFileBytes)
  { Gap(TEXT("ASSET_BYTE_OR_FILE_LIMIT"), Filename); bStopped = true; return false; }
  TUniquePtr<FArchive> Reader(IFileManager::Get().CreateFileReader(*Filename));
  if (!Reader || Reader->TotalSize() != Before.FileSize)
  { Gap(TEXT("FILE_OPEN_OR_SIZE"), Filename); return false; }
#if PLATFORM_MAC
  CC_SHA256_CTX Context;
  if (!CC_SHA256_Init(&Context)) { Gap(TEXT("SHA256_UNAVAILABLE"), Filename); return false; }
  TArray<uint8> Buffer; Buffer.SetNumUninitialized(1 << 20);
  int64 Remaining = Before.FileSize;
  while (Remaining && Budget())
  {
   int64 Chunk = FMath::Min<int64>(Remaining, Buffer.Num());
   Reader->Serialize(Buffer.GetData(), Chunk);
   if (Reader->IsError() || !CC_SHA256_Update(&Context, Buffer.GetData(), static_cast<CC_LONG>(Chunk)))
   { Gap(TEXT("FILE_READ_OR_HASH"), Filename); return false; }
   Remaining -= Chunk; BytesRead += Chunk;
  }
  if (Remaining) return false;
  uint8 Digest[CC_SHA256_DIGEST_LENGTH];
  if (!CC_SHA256_Final(Digest, &Context)) { Gap(TEXT("SHA256_UNAVAILABLE"), Filename); return false; }
  Hash = BytesToHex(Digest, CC_SHA256_DIGEST_LENGTH).ToLower();
#else
  Gap(TEXT("SHA256_UNAVAILABLE"), Filename); return false;
#endif
  FFileStatData After = IFileManager::Get().GetStatData(*Filename);
  if (!After.bIsValid || After.bIsDirectory || Before.FileSize != After.FileSize || Before.ModificationTime != After.ModificationTime)
  { Gap(TEXT("FILE_CHANGED_DURING_HASH"), Filename); return false; }
  Count = Before.FileSize; UniqueFileBytes += Count; FileNames.Add(Filename); FileStats.Add(After);
  J F = Object(); F->SetStringField(TEXT("path"), Filename); F->SetNumberField(TEXT("byte_count"), double(Count)); F->SetStringField(TEXT("sha256"), Hash);
  F->SetStringField(TEXT("mtime_ticks_before"), LexToString(Before.ModificationTime.GetTicks())); F->SetStringField(TEXT("mtime_ticks_after"), LexToString(After.ModificationTime.GetTicks()));
  Files.Add(F); return true;
 }
 void InspectSummary(const FString& Filename, J Node)
 {
  TUniquePtr<FArchive> Reader(IFileManager::Get().CreateFileReader(*Filename));
  if (!Reader) { Gap(TEXT("PACKAGE_HEADER_UNAVAILABLE"), Filename); return; }
  FPackageFileSummary Summary; *Reader << Summary;
  if (Reader->IsError() || (uint32(Summary.Tag) != 0x9e2a83c1U && uint32(Summary.Tag) != 0xc1832a9eU) || !Summary.IsFileVersionValid() || Summary.IsFileVersionTooOld() || Summary.IsFileVersionTooNew() || Summary.TotalHeaderSize <= 0 || Summary.TotalHeaderSize > Reader->TotalSize()) { Gap(TEXT("PACKAGE_HEADER_INVALID"), Filename); return; }
  Node->SetNumberField(TEXT("package_flags"), double(Summary.GetPackageFlags()));
  Node->SetStringField(TEXT("payload_toc_offset"), LexToString(Summary.PayloadTocOffset));
  if (Summary.GetPackageFlags() & (PKG_Cooked | PKG_FilterEditorOnly)) Gap(TEXT("COOKED_PACKAGE_GAP"), Filename);
  UE::FPackageTrailer Trailer;
  bool HasTrailer = UE::FPackageTrailer::TryLoadFromFile(Filename, Trailer);
  Node->SetBoolField(TEXT("trailer_present"), HasTrailer);
  if (Summary.DataResourceOffset > 0) Gap(TEXT("DATA_RESOURCE_TABLE_UNSUPPORTED"), Filename);
  if (Summary.BulkDataStartOffset > Reader->TotalSize()) Gap(TEXT("EXTERNAL_BULK_OFFSET"), Filename);
  if (!HasTrailer && Summary.PayloadTocOffset >= 0) Gap(TEXT("TRAILER_UNAVAILABLE"), Filename);
  if (HasTrailer)
  {
   int32 Virtual = Trailer.GetNumPayloads(UE::EPayloadStorageType::Virtualized);
   int32 Referenced = Trailer.GetNumPayloads(UE::EPayloadStorageType::Referenced);
   Node->SetNumberField(TEXT("virtualized_payloads"), Virtual); Node->SetNumberField(TEXT("referenced_payloads"), Referenced);
   if (Virtual || Referenced) Gap(TEXT("EXTERNAL_PAYLOAD_GAP"), Filename);
  }
 }
 void ReadContent(FName Package)
 {
  if (!Budget()) return;
  if (Nodes.Num() >= MaxNodes) { Gap(TEXT("ASSET_COUNT_LIMIT"), Package.ToString()); bStopped = true; return; }
  FString Filename;
  if (!FPackageName::DoesPackageExist(Package.ToString(), &Filename, false))
  { Gap(TEXT("PACKAGE_FILE_MISSING"), Package.ToString()); return; }
  Filename = FPaths::ConvertRelativePathToFull(Filename); FPaths::NormalizeFilename(Filename);
  if (!Prefix(Filename, EngineContent) || !Same(FPaths::GetExtension(Filename), TEXT("uasset")))
  { Gap(TEXT("UNSUPPORTED_SOURCE_PATH"), Filename); return; }
  Registry.ScanFilesSynchronous({Filename}, true);
  TArray<FAssetData> Assets;
  if (!Registry.GetAssetsByPackageName(Package, Assets, true, false) || Assets.Num() != 1)
  { Gap(TEXT("MISSING_OR_AMBIGUOUS_ASSET"), Package.ToString()); return; }
  FNode N; N.Package = Package; N.Uri = Assets[0].GetSoftObjectPath().ToString();
  if (!AssetUri(N.Uri)) { Gap(TEXT("URI_SCHEMA_GAP"), N.Uri); return; }
  N.PrimaryFile = Filename;
  FString UriHash = AsciiSha(N.Uri);
  if (UriHash.Len() != 64) Gap(TEXT("ASSET_ID_HASH_UNAVAILABLE"), N.Uri);
  N.Id = TEXT("asset-") + UriHash.Left(58);
  for (int32 I = 0; I < 4; ++I) if (Same(N.Uri, Roots[I])) N.Id = RootIds[I];
  if (!Identifier(N.Id)) Gap(TEXT("ASSET_ID_HASH_UNAVAILABLE"), N.Uri);
  N.Audit->SetStringField(TEXT("package"), Package.ToString()); N.Audit->SetStringField(TEXT("uri"), N.Uri); N.Audit->SetStringField(TEXT("asset_id"), N.Id);
  N.Audit->SetStringField(TEXT("asset_class"), Assets[0].AssetClassPath.ToString());
  InspectSummary(Filename, N.Audit);
  TArray<FString> Siblings;
  const FString Stem = FPaths::GetBaseFilename(Filename);
  const FString Directory = FPaths::GetPath(Filename);
  IFileManager::Get().FindFiles(Siblings, *(Directory / (Stem + TEXT(".*"))), true, false);
  Siblings.Sort(Less);
  if (Siblings.Num() > 16) { Gap(TEXT("SIDECAR_FILE_LIMIT"), Filename); bStopped = true; }
  for (int32 I = 0; I < FMath::Min(Siblings.Num(), 16); ++I)
  {
   FString Path = Directory / Siblings[I], Sha; int64 Size = 0;
   if (!Same(Path, Filename)) Gap(TEXT("ASSET_SCHEMA_GAP_SIDECAR"), Path);
   if (HashFile(Path, Sha, Size) && Same(Path, Filename)) { N.Sha = Sha; N.PrimaryBytes = Size; }
  }
  if (N.Sha.IsEmpty()) Gap(TEXT("PRIMARY_HASH_MISSING"), Filename);
  Nodes.Add(MoveTemp(N));
 }
 void Walk(FName Package)
 {
  if (!Budget() || Seen.Contains(Package)) return;
  if (Seen.Num() >= 128) { Gap(TEXT("REGISTRY_NODE_LIMIT"), Package.ToString()); bStopped = true; return; }
  Seen.Add(Package);
  const FString Name = Package.ToString();
  if (Prefix(Name, TEXT("/Script/")))
  {
   UPackage* P = FindPackage(nullptr, *Name);
   if (!P || !P->HasAnyPackageFlags(PKG_CompiledIn)) Gap(TEXT("UNRESOLVED_NATIVE_TERMINAL"), Name);
   else Native.Add(Package);
   return;
  }
  if (!Prefix(Name, TEXT("/Engine/"))) { Gap(TEXT("EXTERNAL_MOUNT_GAP"), Name); return; }
  ReadContent(Package);
  TArray<FAssetDependency> All;
  bool Queried = Registry.GetDependencies(FAssetIdentifier(Package), All, UE::AssetRegistry::EDependencyCategory::All, UE::AssetRegistry::FDependencyQuery());
  if (!Queried) { Gap(TEXT("REGISTRY_DEPENDENCIES_UNAVAILABLE"), Name); return; }
  All.Sort([](const FAssetDependency& A, const FAssetDependency& B) { return A.LexicalLess(B); });
  TArray<FName> Content;
  for (const FAssetDependency& D : All)
  {
   if (Edges.Num() >= MaxEdges) { Gap(TEXT("REGISTRY_EDGE_LIMIT"), Name); bStopped = true; break; }
   J Edge = Object(); Edge->SetStringField(TEXT("from"), Name); Edge->SetStringField(TEXT("target"), D.AssetId.ToString());
   Edge->SetNumberField(TEXT("category"), uint8(D.Category)); Edge->SetNumberField(TEXT("properties"), uint8(D.Properties)); Edges.Add(Edge);
   if (D.Category == UE::AssetRegistry::EDependencyCategory::Package)
   {
    if (!D.AssetId.IsPackage()) Gap(TEXT("NONPACKAGE_CONTENT_EDGE"), D.AssetId.ToString());
    else Content.AddUnique(D.AssetId.PackageName);
   }
  }
  for (FNode& N : Nodes) if (N.Package == Package) { N.Dependencies = Content; break; }
  for (FName Target : Content) Walk(Target);
 }
 FString Candidate(const FString& WorldId)
 {
  FString Entries = TEXT("[");
  Nodes.Sort([](const FNode& A, const FNode& B) { return Less(A.Id, B.Id); });
  for (int32 I = 0; I < Nodes.Num(); ++I)
  {
   const FNode& N = Nodes[I]; if (I) Entries += TEXT(",");
   TArray<FString> DependencyIds;
   for (FName D : N.Dependencies)
   {
    if (Native.Contains(D)) continue;
    bool Found = false;
    for (const FNode& Other : Nodes) if (Other.Package == D) { DependencyIds.Add(Other.Id); Found = true; break; }
    if (!Found) Gap(TEXT("CONTENT_DEPENDENCY_MISSING"), D.ToString());
   }
   DependencyIds.Sort(Less);
   FString Dependencies = TEXT("[");
   for (int32 K = 0; K < DependencyIds.Num(); ++K) { if (K) Dependencies += TEXT(","); Dependencies += TEXT("\"") + DependencyIds[K] + TEXT("\""); }
   Dependencies += TEXT("]");
   Entries += TEXT("{\"asset_id\":\"") + N.Id + TEXT("\",\"byte_count\":") + LexToString(N.PrimaryBytes)
    + TEXT(",\"content_sha256\":\"") + N.Sha + TEXT("\",\"dependencies\":") + Dependencies
    + TEXT(",\"license_status\":\"ue-installed-content-no-shipping-review\",\"source\":\"installed-ue-5.8.3-basicshapes\",\"uri\":\"") + N.Uri + TEXT("\",\"use\":\"technical-proxy-not-realism\"}");
  }
  Entries += TEXT("]");
  return TEXT("{\"body\":{\"dependency_status\":\"runtime-resolved\",\"entries\":") + Entries
   + TEXT("},\"domain\":\"edgeworld.universe.authority\",\"id\":\"asset-manifest-runtime\",\"kind\":\"asset_manifest\",\"refs\":{},\"version\":\"0.2\",\"world_id\":\"") + WorldId + TEXT("\"}");
 }
 void VerifyGraph()
 {
  for (const TCHAR* Root : Roots)
   if (!Nodes.ContainsByPredicate([&](const FNode& N) { return Same(N.Uri, Root); })) Gap(TEXT("ROOT_NOT_IN_FINAL_GRAPH"), Root);
  TArray<FName> Active, Done;
  TFunction<void(FName)> Visit = [&](FName P)
  {
   if (Native.Contains(P) || Done.Contains(P) || !Budget()) return;
   if (Active.Contains(P)) { Gap(TEXT("ASSET_GRAPH_CYCLE"), P.ToString()); return; }
   const FNode* N = Nodes.FindByPredicate([&](const FNode& Row) { return Row.Package == P; });
   if (!N) { Gap(TEXT("CONTENT_DEPENDENCY_MISSING"), P.ToString()); return; }
   Active.Add(P); for (FName D : N->Dependencies) Visit(D); Active.Remove(P); Done.Add(P);
  };
  for (const FNode& N : Nodes) Visit(N.Package);
  for (int32 I = 0; I < Nodes.Num(); ++I)
   for (int32 K = I + 1; K < Nodes.Num(); ++K)
    if (Same(Nodes[I].Id, Nodes[K].Id) || Same(Nodes[I].Uri, Nodes[K].Uri)) Gap(TEXT("ASSET_ID_OR_URI_COLLISION"), Nodes[I].Uri);
  for (int32 I = 0; I < FileNames.Num(); ++I)
  {
   FFileStatData Now = IFileManager::Get().GetStatData(*FileNames[I]);
   if (!Now.bIsValid || Now.FileSize != FileStats[I].FileSize || Now.ModificationTime != FileStats[I].ModificationTime)
    Gap(TEXT("FILE_CHANGED_AFTER_SCAN"), FileNames[I]);
  }
 }
 bool Run(const FString& WorldId, FEdgeWorldUniverseAssetAuditResult& Out)
 {
  const FEngineVersion& Version = FEngineVersion::Current();
  if (Version.GetMajor() != 5 || Version.GetMinor() != 8 || Version.GetPatch() != 3 || Version.GetChangelist() != 58210709)
   Gap(TEXT("ENGINE_BUILD_MISMATCH"), Version.ToString());
  Registry.SearchAllAssets(true); Registry.WaitForCompletion();
  if (Registry.IsLoadingAssets()) Gap(TEXT("REGISTRY_STILL_LOADING"), TEXT("after explicit synchronous scan"));
  TArray<FString> RootStrings;
  for (const TCHAR* Root : Roots)
  {
   RootStrings.Add(Root);
   FAssetData Data = Registry.GetAssetByObjectPath(FSoftObjectPath(Root), true, false);
   if (!Data.IsValid() || !Same(Data.GetSoftObjectPath().ToString(), Root)) Gap(TEXT("ROOT_ASSET_MISSING_OR_ALIAS"), Root);
   else Walk(Data.PackageName);
  }
  VerifyGraph();
  FString Canon, Digest, CodecError;
  if (Gaps.IsEmpty())
  {
   FString Raw = Candidate(WorldId); FTCHARToUTF8 Utf8(*Raw);
   if (Gaps.IsEmpty() && FEdgeWorldUniverseObservationParser::CanonicalRecord(MakeArrayView(reinterpret_cast<const uint8*>(Utf8.Get()), Utf8.Length()), Canon, Digest, CodecError))
   { Out.CandidateJson = Canon; Out.CandidateDigest = Digest; Out.bResolved = true; }
   else Gap(TEXT("CANDIDATE_SCHEMA_GAP"), CodecError);
  }
  J Audit = Object(); Audit->SetStringField(TEXT("audit_version"), TEXT("registry-package-content.v0.1")); Audit->SetStringField(TEXT("world_id"), WorldId);
  Audit->SetStringField(TEXT("ue_version"), Version.ToString()); Audit->SetArrayField(TEXT("seed_uris"), Strings(RootStrings));
  Audit->SetStringField(TEXT("graph_policy"), TEXT("all-on-disk-Package-properties; loaded-compiled-in-Script-terminals; Manage/SearchableName-audited-not-content"));
  Audit->SetBoolField(TEXT("resolved"), Out.bResolved); Audit->SetNumberField(TEXT("A_declared"), 4);
  if (Out.bResolved) { Audit->SetNumberField(TEXT("A_actual"), Nodes.Num()); Audit->SetNumberField(TEXT("asset_bytes_actual"), double(UniqueFileBytes)); }
  else { Audit->SetField(TEXT("A_actual"), MakeShared<FJsonValueNull>()); Audit->SetField(TEXT("asset_bytes_actual"), MakeShared<FJsonValueNull>()); }
  Audit->SetNumberField(TEXT("observed_content_nodes"), Nodes.Num()); Audit->SetNumberField(TEXT("observed_file_bytes"), double(UniqueFileBytes)); Audit->SetNumberField(TEXT("stream_bytes_read"), double(BytesRead));
  TArray<TSharedPtr<FJsonValue>> NodeValues, NativeValues, EdgeValues, FileValues, GapValues;
  Nodes.Sort([](const FNode& A, const FNode& B) { return Less(A.Uri, B.Uri); });
  for (const FNode& N : Nodes) { N.Audit->SetStringField(TEXT("primary_sha256"), N.Sha); N.Audit->SetNumberField(TEXT("primary_bytes"), double(N.PrimaryBytes)); N.Audit->SetArrayField(TEXT("package_dependencies"), Strings([&]() { TArray<FString> Ds; for(FName D:N.Dependencies)Ds.Add(D.ToString());Ds.Sort(Less);return Ds; }())); NodeValues.Add(MakeShared<FJsonValueObject>(N.Audit)); }
  Native.Sort(FNameLexicalLess());
  for (FName P : Native) { J Row = Object(); Row->SetStringField(TEXT("package"), P.ToString()); Row->SetBoolField(TEXT("compiled_in_loaded"), true); Row->SetNumberField(TEXT("package_flags"), double(FindPackage(nullptr, *P.ToString())->GetPackageFlags())); NativeValues.Add(MakeShared<FJsonValueObject>(Row)); }
  for (const J& X : Edges) EdgeValues.Add(MakeShared<FJsonValueObject>(X));
  for (const J& X : Files) FileValues.Add(MakeShared<FJsonValueObject>(X));
  for (const J& X : Gaps) GapValues.Add(MakeShared<FJsonValueObject>(X));
  Audit->SetArrayField(TEXT("content_nodes"), NodeValues); Audit->SetArrayField(TEXT("native_terminals"), NativeValues); Audit->SetArrayField(TEXT("registry_edges_all_categories"), EdgeValues); Audit->SetArrayField(TEXT("files"), FileValues); Audit->SetArrayField(TEXT("gaps"), GapValues);
  if (Out.bResolved) { J Record; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Out.CandidateJson), Record); Audit->SetObjectField(TEXT("candidate_manifest"), Record); Audit->SetStringField(TEXT("candidate_digest"), Out.CandidateDigest); }
  else { Audit->SetField(TEXT("candidate_manifest"), MakeShared<FJsonValueNull>()); Audit->SetField(TEXT("candidate_digest"), MakeShared<FJsonValueNull>()); }
  Out.AuditJson = Json(Audit); Out.AssetCount = Nodes.Num(); Out.NativeTerminalCount = Native.Num(); Out.GapCount = Gaps.Num(); Out.ObservedFileBytes = UniqueFileBytes;
  return true;
 }
};
}
bool FEdgeWorldUniverseAssetAudit::Collect(const FString& WorldId, FEdgeWorldUniverseAssetAuditResult& Out, FString& Error)
{
 Out = FEdgeWorldUniverseAssetAuditResult(); Error.Reset();
 if (!UniverseAssetAudit::Identifier(WorldId) || !IsInGameThread() || !GIsEditor || !GEngine || !GEngine->IsInitialized())
 { Error = TEXT("Explicit editor game-thread audit and valid owner world ID required"); return false; }
 auto& Module = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
 UniverseAssetAudit::FCollector Collector(Module.Get());
 return Collector.Run(WorldId, Out);
}
#endif

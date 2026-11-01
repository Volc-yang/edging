#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EdgeWorldUniverseObservation.h"
#include "EdgeWorldUniverseActor.generated.h"
UCLASS()
class EDGEWORLDHOST_API AEdgeWorldUniverseActor : public AActor
{
 GENERATED_BODY()
public:
 AEdgeWorldUniverseActor();
 bool ApplyVerified(const FEdgeWorldUniverseObservation& Observation,FString& Error);
 void SetProjectionVisible(bool Visible);
 int32 GetDerivedInstanceCount()const{return DerivedInstances;}
 static FVector Position(const FEdgeWorldUniverseObservation& O,const FVector3d& M){return FVector(O.OriginCm+FVector3d(M.X,-M.Y,M.Z)*O.Scale);}
 static FQuat Quaternion(const FVector4d& WXYZ){return FQuat(-WXYZ.Y,WXYZ.Z,-WXYZ.W,WXYZ.X);}
 static FVector LinearVelocity(const FVector3d& V,double Scale){return FVector(V.X,-V.Y,V.Z)*Scale;}
 static FVector AngularVelocity(const FVector3d& V){return FVector(-V.X,V.Y,-V.Z);}
private:
 UPROPERTY() TArray<TObjectPtr<AActor>> Proxies;
 int32 DerivedInstances=0;
 bool bProjectionVisible=true;
};

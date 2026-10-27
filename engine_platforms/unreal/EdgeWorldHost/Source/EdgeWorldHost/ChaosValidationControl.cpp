#include "ChaosValidationControl.h"

#include "ChaosObservationGameMode.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

FChaosValidationControl::FChaosValidationControl(AChaosObservationGameMode* InMode,
	FString InCommandPath, FString InAckPath)
	: Mode(InMode), CommandPath(MoveTemp(InCommandPath)), AckPath(MoveTemp(InAckPath))
{
	TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateRaw(this, &FChaosValidationControl::Poll), 0.1f);
}

FChaosValidationControl::~FChaosValidationControl()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
}

bool FChaosValidationControl::Poll(float)
{
	if (!Mode.IsValid()) return false;
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *CommandPath)) return true;
	TSharedPtr<FJsonObject> Command;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Command)
		|| !Command.IsValid()) return true; // External writer may still be replacing the file.
	int64 Sequence = -1;
	if (!Command->TryGetNumberField(TEXT("seq"), Sequence) || Sequence <= LastSequence) return true;
	LastSequence = Sequence;
	FString Action;
	Command->TryGetStringField(TEXT("action"), Action);
	FString Detail;
	const bool bApplied = Mode->ExecuteValidationCommand(Command, Detail);
	TSharedRef<FJsonObject> Ack = MakeShared<FJsonObject>();
	Ack->SetNumberField(TEXT("seq"), static_cast<double>(Sequence));
	Ack->SetStringField(TEXT("action"), Action);
	Ack->SetBoolField(TEXT("applied"), bApplied);
	Ack->SetStringField(TEXT("detail"), Detail);
	FString Line;
	FJsonSerializer::Serialize(Ack,
		TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Line));
	if (!FFileHelper::SaveStringToFile(Line + TEXT("\n"), *AckPath,
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append))
	{
		UE_LOG(LogTemp, Error, TEXT("ChaosValidation acknowledgement write failed: %s"), *AckPath);
	}
	UE_LOG(LogTemp, Display, TEXT("ChaosValidation seq=%lld action=%s applied=%s detail=%s"),
		static_cast<long long>(Sequence), *Action, bApplied ? TEXT("true") : TEXT("false"), *Detail);
	return true;
}

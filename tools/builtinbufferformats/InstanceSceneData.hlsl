// Refs: SceneData.ush::GetInstanceSceneData(uint InstanceId, uint SOAStride, bool bCheckValid = true)
// Macros: PLATFORM_ALLOW_SCENE_DATA_COMPRESSED_TRANSFORMS = 1

#define View_InstanceSceneDataSOAStride 64

struct FInstanceInfo
{
    uint PrimitiveId : 20;
    uint PrimitiveFlags : 12;
    uint RelativeId : 24;
    uint CustomDataCount : 8;
    uint LastUpdateSceneFrameNumber;
    float RandomID;
};

struct FRotationScale
{
    uint3 Rotation;
    uint Scale;
};

struct FTranslation
{
    float3 Translation;
    float Padding;
};


[[fixed]]
struct Data
{
    FInstanceInfo InstanceInfo[View_InstanceSceneDataSOAStride];
    FRotationScale CurrRotationScale[View_InstanceSceneDataSOAStride];
    FTranslation CurrTranslation[View_InstanceSceneDataSOAStride];
    FRotationScale PrevRotationScale[View_InstanceSceneDataSOAStride];
    FTranslation PrevTranslation[View_InstanceSceneDataSOAStride];
};


// Refs: SceneData.ush::GetPrimitiveData(uint PrimitiveId)

#define NUM_CUSTOM_PRIMITIVE_DATA 9

struct FPrimitiveSceneData
{
	// 0
	uint		Flags; // TODO: Use 16 bits?
	int			InstanceSceneDataOffset; // Link to the range of instances that belong to this primitive
	int			NumInstanceSceneDataEntries;
	uint		SingleCaptureIndex; // TODO: Use 16 bits? 8 bits?

	// 1
	float3		TilePosition;
	uint		PrimitiveComponentId; // TODO: Refactor to use PersistentPrimitiveIndex, ENGINE USE ONLY - will be removed
	// 2,3,4,5
	float4x4	LocalToWorld;
	// 6,7,8,9
	float4x4 	WorldToLocal;
	// 10,11,12,13
	float4x4	PreviousLocalToWorld;
	// 14,15,16,17
	float4x4 	PreviousWorldToLocal;
	// 18
	float3		InvNonUniformScale;
	float		ObjectBoundsX;
	// 19
	float3 		ObjectWorldPosition;
	float		ObjectRadius;
	// 20
	float3 		ActorWorldPosition;
	uint		LightmapUVIndex;   // TODO: Use 16 bits? // TODO: Move into associated array that disappears if static lighting is disabled
	// 21
	float3		ObjectOrientation; // TODO: More efficient representation?
	uint		LightmapDataIndex; // TODO: Use 16 bits? // TODO: Move into associated array that disappears if static lighting is disabled
	// 22
	float4		NonUniformScale;
	// 23
	float3		PreSkinnedLocalBoundsMin;
	uint		NaniteResourceID;
	// 24
	float3		PreSkinnedLocalBoundsMax;
	uint		NaniteHierarchyOffset;
	// 25
	float3		LocalObjectBoundsMin;
	float		ObjectBoundsY;
	// 26
	float3		LocalObjectBoundsMax;
	float		ObjectBoundsZ;
	// 27
	float3		InstanceLocalBoundsCenter;
	uint		InstancePayloadDataOffset;
	// 28
	float3		InstanceLocalBoundsExtent;
	uint		InstancePayloadDataStride; // TODO: Use 16 bits? 8 bits?
	// 29
	float3		WireframeColor; // TODO: Should refactor out all editor data into a separate buffer
	uint		PackedNaniteFlags;
	// 30
	float3		LevelColor; // TODO: Should refactor out all editor data into a separate buffer
	int			PersistentPrimitiveIndex;
	// 31
	float2 		InstanceDrawDistanceMinMaxSquared;
	float		InstanceWPODisableDistanceSquared;
	uint		NaniteRayTracingDataOffset;
	// 32
	float		BoundsScale;
	float3		Unused;
	// 33+
	float4		CustomPrimitiveData[NUM_CUSTOM_PRIMITIVE_DATA]; // TODO: Move to associated array to shrink primitive data and pack cachelines more effectively
};
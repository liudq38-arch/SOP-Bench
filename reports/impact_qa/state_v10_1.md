# state_v10_1 开放题开发样本

3 个 front 装配视频；源标注辅助文本生成，视频单独核验；全部待真人审核。

```json
{
  "version": "state_v10_1",
  "events": 12,
  "videos": 3,
  "status": {
    "ok": 10,
    "error": 2
  },
  "qa_pairs": 20,
  "types": {
    "completion": 10,
    "reference_order": 10
  },
  "answer_polarities": {
    "yes": 17,
    "no": 3
  },
  "machine_decisions": {
    "keep_candidate": 14,
    "needs_evidence": 6
  },
  "structural_issue_pairs": 0,
  "deferred_types": {
    "install_relation": 9
  },
  "human_reviewed": 0,
  "limits": "Development only. Same-model screening is not accuracy. Illustrated sequence is not an exhaustive mandatory-order graph. All pending_human_review."
}
```

## AL07EJ17_Reassembly_A_002_front__adapter_done__state_v10_1_0

Was the adapter plate correctly installed by the end of the video?

Yes, the adapter plate was correctly installed by the end.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the adapter plate is correctly assembled (state 1) at the end of the video. The visual evidence shows the operator completing the installation and fastening of the adapter plate, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__adapter_done__state_v10_1_1

As shown in the supplied guide, was the gearbox housing completed before starting to attach the adapter plate?

Yes, the gearbox housing was completed before the adapter plate attachment began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the gearbox housing reached state 1 (completed) at frame 982, which precedes the start of the adapter plate attachment action at frame 1040. The video visually confirms the housing is assembled and the operator proceeds to attach the adapter plate, consistent with the source data.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_done__state_v10_1_0

Was the bearing plate correctly installed by the end of the clip?

Yes, the bearing plate was correctly installed by the end of the clip.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator performing the action of inserting and screwing the bearing plate, but the final state (fully seated and secured) is not clearly visible due to the camera angle and occlusion by the operator's hands and the tool."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The source annotations explicitly state the bearing plate is correctly assembled (state 1) at the end of the clip. However, the visual evidence is insufficient to independently confirm this final state; the video cuts while the operator is still working on the screws, and the final result is obscured.", "requested_evidence": ["Clear view of the bearing plate fully seated and secured with screws at the end of the action."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_done__state_v10_1_1

Was the adapter plate completed before starting the bearing plate step as shown in the supplied guide?

Yes, the adapter plate was completed before the bearing plate step began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the adapter plate reached state 1 (completed) at frame 2480 (approx 82.6s), which precedes the start of the bearing plate insertion action at 85.5s. The video visually confirms the adapter plate is installed and the operator proceeds to insert the bearing plate, consistent with the reference order.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_incomplete__state_v10_1_0

Was the bearing plate correctly installed by the end of the video?

No, the bearing plate was not correctly installed at the end.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator inserting the bearing plate and beginning to screw it in, but the clip ends before the action is visibly completed or the final state is confirmed. The 'misassembled' state is derived from the source annotation, not directly observable as a specific error in the provided frames."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The reference answer is supported by the source state annotation (state -1 at end), but the video itself cuts off while the action is still in progress. The visual evidence is insufficient to independently confirm the 'misassembled' state or the completion of the step without relying on the annotation.", "requested_evidence": ["Video frames extending beyond 96.1s to show the final state of the bearing plate installation."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_incomplete__state_v10_1_1

Was the adapter plate completed before starting the bearing plate step as shown in the supplied guide?

Yes, the adapter plate was correctly assembled before the bearing plate step began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the adapter plate was in state 1 (correctly assembled) at frame 2480, which precedes the start of the bearing plate action at frame 2567. The video visually confirms the adapter plate is attached and the operator proceeds to the bearing plate step, consistent with the guide's sequence.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__handle_done__state_v10_1_0

Was the anti_vibration_handle correctly installed by the end of the video?

Yes, the anti_vibration_handle was correctly installed.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the anti_vibration_handle is in state 1 (correctly assembled) at the end of the video. The visual evidence shows the handle attached to the gearbox housing at the final frames, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__handle_done__state_v10_1_1

Was the lever completed before starting to screw on the anti_vibration_handle, as shown in the supplied guide?

Yes, the lever was completed before the anti_vibration_handle installation began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the lever assembly was completed (state 1) at frame 4774, prior to the start of the handle installation at frame 4826. The video visually confirms the lever is installed on the tool before the operator picks up and screws on the handle.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__adapter_done__state_v10_1_0

Was the adapter plate correctly installed by the end of the video?

Yes, the adapter plate was correctly installed by the end.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the adapter plate is correctly assembled (state 1) at the end of the clip. The video visually confirms the operator completing the screwing action and the plate being attached to the housing, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__adapter_done__state_v10_1_1

As shown in the supplied guide, was the gearbox housing completed before starting to attach the adapter plate?

Yes, the gearbox housing was completed before the adapter plate attachment began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the gearbox housing is in state 1 (completed) at frame 862 (approx 28.7s), which precedes the start of the adapter plate attachment action at 31.5s. The video visually confirms the housing is assembled and the operator proceeds to attach the adapter plate, consistent with the source timeline.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_done__state_v10_1_0

Was the bearing plate correctly installed by the end of the clip?

Yes, the bearing plate was correctly installed by the end of the clip.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["Final state of the bearing plate is not visually verifiable from the provided frames due to occlusion by the operator's hands and the angle of the device.", "The video shows the operator performing the action of inserting and adjusting the plate, but the final 'correctly installed' state (e.g., flush fit, screws tightened) is not explicitly visible in the last frame."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The source annotations explicitly state the bearing plate is correctly assembled (state 1) at the end of the clip. However, the visual evidence is insufficient to independently confirm this state as the final result is obscured. The answer relies on the source label rather than visible confirmation.", "requested_evidence": ["Frame showing the bearing plate fully seated and secured without obstruction."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_done__state_v10_1_1

Was the adapter plate completed before starting the bearing plate step as shown in the supplied guide?

Yes, the adapter plate was completed before the bearing plate step began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "Source annotations confirm the adapter plate reached state 1 (completed) at frame 2470, prior to the bearing plate step starting at frame 2552. The video visually supports this sequence, showing the adapter plate installed before the operator begins handling the bearing plate.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_incomplete__state_v10_1_0

Was the bearing plate correctly installed by the end of the video?

No, the bearing plate was not correctly installed at the end.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator inserting the bearing plate and beginning to screw it in, but the clip ends before the fastening is completed or the final state is visually confirmed. The 'misassembled' state (-1) is derived from the source annotation, not directly observable as a specific error in the provided frames."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The reference answer is supported by the source state annotation (state -1 at end), but the visual evidence is insufficient to independently verify the 'misassembled' condition or confirm the action was not completed. The video cuts off during the process.", "requested_evidence": ["Visual confirmation of the bearing plate's final state (e.g., loose, misaligned, or fully seated) at the end of the clip."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_incomplete__state_v10_1_1

Was the adapter plate completed before starting the bearing plate step as shown in the supplied guide?

Yes, the adapter plate was correctly assembled before the bearing plate step began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations (asr:AL07EJ17_Reassembly_A_003_front:6) explicitly state the adapter_plate is in state 1 (correctly assembled) at frame 2470 (82.3s). The bearing plate action begins at 85.06s. The video visually confirms the adapter plate is installed and the user is working on the bearing plate, consistent with the source data.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__adapter_done__state_v10_1_0

Was the adapter plate correctly installed by the end of the video?

Yes, the adapter plate was correctly installed by the end.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the adapter plate is correctly assembled (state 1) at the end of the video. The visual evidence shows the operator completing the installation and fastening of the adapter plate, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__adapter_done__state_v10_1_1

Was the gearbox housing completed before starting to attach the adapter plate, as shown in the supplied guide?

Yes, the gearbox housing was completed before the adapter plate attachment began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the gearbox housing is in state 1 (completed) at frame 1078 (approx 36s), which precedes the start of the adapter plate attachment at frame 1152 (approx 38.4s). The video visually confirms the housing is assembled and the operator proceeds to attach the adapter plate, consistent with the source timeline.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_done__state_v10_1_0

Was the bearing plate correctly installed by the end of the video?

Yes, the bearing plate was correctly installed by the end of the video.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["Low resolution and motion blur in the final frames prevent independent visual confirmation of the bearing plate's final seated state and screw tightness.", "The video ends immediately after the operator finishes the action, leaving no time to observe the stable end state."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The source annotations explicitly state the bearing plate is correctly assembled (state 1) at the end of the clip. However, the visual evidence is insufficient to independently verify this state due to image quality and the abrupt end of the video. The answer relies on the source label rather than clear visual proof.", "requested_evidence": ["Higher resolution frames of the final assembly state.", "Video footage extending slightly beyond the completion of the action to show the stable result."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_done__state_v10_1_1

Was the adapter plate completed before starting the bearing plate step as shown in the supplied guide?

Yes, the adapter plate was completed before the bearing plate step began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "Source annotations confirm the adapter plate state is 1 (completed) at frame 2535, which precedes the start of the bearing plate insertion action at frame 2647 (88.2s). The video visually supports this sequence, showing the adapter plate installed before the bearing plate is handled.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_incomplete__state_v10_1_0

Was the bearing plate correctly installed by the end of the video?

No, the bearing plate was not correctly installed at the end.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator inserting the bearing plate and manipulating it, but the final state (misassembled vs. correctly seated) is not visually resolvable from the provided frames due to occlusion and lack of clear visual cues for 'misassembly'."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The reference answer is supported by the source state annotation (state -1 at end), but the video itself does not clearly show the specific misassembly condition. The visual evidence is insufficient to independently verify the 'misassembled' claim without relying on the annotation.", "requested_evidence": ["Clear visual confirmation of the bearing plate's final position relative to the housing or screws to verify the misassembly state."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_incomplete__state_v10_1_1

Was the adapter plate completed before starting the bearing plate step as shown in the supplied guide?

Yes, the adapter plate was correctly assembled before the bearing plate step began.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source data (ASR state 6) confirms the adapter plate was in state 1 (correctly assembled) at frame 2535, which precedes the start of the bearing plate action at frame 2647 (approx 88s). The video visually supports this sequence, showing the adapter plate being secured before the bearing plate is retrieved and inserted.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

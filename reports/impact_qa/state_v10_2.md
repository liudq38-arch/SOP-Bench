# state_v10_2 开放题开发样本

3 个 front 装配视频；源标注辅助文本生成，视频单独核验；全部待真人审核。

```json
{
  "version": "state_v10_2",
  "events": 12,
  "videos": 3,
  "status": {
    "ok": 12
  },
  "qa_pairs": 24,
  "types": {
    "completion": 9,
    "reference_order": 12,
    "install_relation": 3
  },
  "answer_polarities": {
    "yes": 21,
    "no": 3
  },
  "machine_decisions": {
    "keep_candidate": 18,
    "needs_evidence": 6
  },
  "structural_issue_pairs": 0,
  "deferred_types": {
    "order_compliance": 12,
    "install_relation": 9
  },
  "human_reviewed": 0,
  "limits": "Development only. Same-model screening is not accuracy. Illustrated sequence is not an exhaustive mandatory-order graph. All pending_human_review."
}
```

## AL07EJ17_Reassembly_A_002_front__adapter_done__state_v10_2_0

Had I correctly installed the adapter plate by the end?

Yes, the adapter plate was correctly installed by the end of the segment.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the adapter plate is correctly assembled (state 1) at the end of the segment. The video visually confirms the operator is performing the final tightening actions on the adapter plate screws at the end of the clip, consistent with the completion of the installation.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__adapter_done__state_v10_2_1

Had I installed the gearbox housing before starting to attach the adapter plate, as shown in the supplied guide?

Yes, the gearbox housing was correctly installed before I started attaching the adapter plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source data (ASR state 2) confirms the gearbox housing was in state 1 (correctly assembled) at the start of the adapter plate attachment step. The video visually supports this, showing the housing already installed on the table before the user begins attaching the adapter plate. The answer correctly reflects the sequence shown in the guide and observed in the video.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_incomplete__state_v10_2_0

Had I correctly installed the bearing plate by the end?

No, the bearing plate was not correctly installed by the end.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator inserting the bearing plate and beginning to screw it in, but the clip ends before the action is visibly completed or the final state is confirmed. The 'misassembled' state (-1) is derived from the source annotation, not directly observable as a specific failure mode in the provided frames."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The reference answer is supported by the source state annotation (state -1 at end frame), but the video itself cuts off while the action is still in progress. The visual evidence is insufficient to independently confirm the 'misassembled' state or the completion of the step, making the visual status uncertain.", "requested_evidence": ["Video frames extending beyond 96.1s to show the final state of the bearing plate installation."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_incomplete__state_v10_2_1

Had I installed the adapter plate before starting to insert the bearing plate, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before I started inserting the bearing plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source data (ASR state 6) confirms the adapter plate was in state 1 (correctly assembled) at the start of the bearing plate insertion action (frame 2567 vs 2567). The video visually supports this sequence, showing the adapter plate being secured before the bearing plate is handled. The answer correctly reflects the supported temporal order without making unsupported claims about the final state of the bearing plate.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_done__state_v10_2_0

Had I correctly installed the bearing plate by the end?

Yes, the bearing plate was correctly installed by the end of the segment.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator performing the action of inserting and screwing the bearing plate, but the final state (fully seated and tightened) is not visually confirmed due to the camera angle and occlusion by the operator's hands and the tool."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The source annotations explicitly state the bearing plate is correctly assembled (state 1) at the end of the segment. However, the video only shows the process of installation; the final result is obscured, making visual confirmation of the 'correctly installed' state impossible without relying on the source labels.", "requested_evidence": ["Visual confirmation of the bearing plate being fully seated and secured, or a clear view of the final assembly state."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_done__state_v10_2_1

Had I installed the adapter plate before starting to insert the bearing plate, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before I started inserting the bearing plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations confirm the adapter plate state is 1 (correctly assembled) at frame 2480 (approx 82.7s), which precedes the start of the bearing plate insertion action at 85.6s. The video visually shows the adapter plate installed on the gearbox housing before the operator picks up and inserts the bearing plate. The answer correctly reflects this sequence.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__handle_done__state_v10_2_0

Had I correctly installed the anti-vibration handle into the gearbox housing by the end?

Yes, the anti-vibration handle was correctly installed into the gearbox housing by the end.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the anti-vibration handle is correctly assembled (state 1) at the end of the clip. The video visually confirms the handle is attached to the gearbox housing at the final frames, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__handle_done__state_v10_2_1

Had I installed the locking lever assembly before starting to screw on the anti-vibration handle, as shown in the supplied guide?

Yes, the locking lever assembly was correctly installed before I started to screw on the anti-vibration handle.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the locking lever assembly was installed (state 1) before the handle installation began. The video visually confirms the lever is present on the tool while the user screws on the handle, consistent with the guide's sequence.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__adapter_done__state_v10_2_0

Had I correctly installed the adapter plate by the end?

Yes, the adapter plate was correctly installed by the end of the segment.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the adapter plate is correctly assembled (state 1) at the end of the segment. The video visually confirms the operator is performing the final tightening actions on the adapter plate screws at the end of the clip, consistent with the completion of the task.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__adapter_done__state_v10_2_1

Had I installed the gearbox housing before starting to attach the adapter plate, as shown in the supplied guide?

Yes, the gearbox housing was correctly installed before I started attaching the adapter plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the gearbox housing was in state 1 (correctly assembled) at the start of the adapter plate attachment step (frame 945), which precedes the target action. The video visually confirms the housing is present and the operator proceeds to attach the adapter plate, consistent with the reference order.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_incomplete__state_v10_2_0

Had I correctly installed the bearing plate by the end?

No, the bearing plate was not correctly installed by the end.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator inserting the bearing plate and beginning to screw it in, but the clip ends before the action is visibly completed or the final state is confirmed. The 'misassembled' state (-1) is derived from the source annotation, not directly observable as a specific error in the provided frames."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The answer is supported by the source state annotation (-1), but the visual evidence is insufficient to independently confirm the 'misassembled' state or the specific nature of the error. The video cuts off while the action is ongoing, making the final result uncertain visually.", "requested_evidence": ["Video frames extending beyond 100.5s to show the completion of the bearing plate installation or a clear visual confirmation of the error."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_incomplete__state_v10_2_1

Had I installed the adapter plate before starting to insert the bearing plate, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before I started inserting the bearing plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source data (ASR state 6) confirms the adapter plate was in state 1 (correctly assembled) at the start of the bearing plate insertion action (approx 85s). The video visually supports this sequence, showing the adapter plate installed before the bearing plate is handled. The answer correctly reflects the supported temporal order without making unsupported claims about the final state of the bearing plate.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_done__state_v10_2_0

Had I correctly installed the bearing plate by the end?

Yes, the bearing plate was correctly installed by the end of the segment.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["Final state of the bearing plate is not visually verifiable from the provided frames due to occlusion by the operator's hands and the angle of the device.", "The video shows the operator performing the action of inserting and adjusting the plate, but the final 'correctly installed' state (e.g., flush fit, screws tightened) is not explicitly visible in the last frame."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The source annotations explicitly state the bearing plate is correctly assembled (state 1) at the end. However, the visual evidence is insufficient to independently confirm this state as the final result is obscured. The answer relies on the source label rather than visible confirmation.", "requested_evidence": ["Frame showing the bearing plate fully seated and secured without obstruction."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__bearing_done__state_v10_2_1

Had I installed the adapter plate before starting to insert the bearing plate, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before I started inserting the bearing plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations confirm the adapter plate state is 1 (correctly assembled) at frame 2470 (approx 82s), which precedes the start of the bearing plate insertion action at 85.06s. The video visually supports this sequence, showing the adapter plate installed before the operator begins handling the bearing plate.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__handle_done__state_v10_2_0

Had I correctly installed the anti-vibration handle into the gearbox housing by the end?

Yes, the anti-vibration handle was correctly installed into the gearbox housing by the end.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the anti-vibration handle is correctly assembled (state 1) at the end of the segment. The video visually confirms the handle is attached to the gearbox housing at the final frames, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_003_front__handle_done__state_v10_2_1

Had I installed the locking lever assembly before starting to screw on the anti-vibration handle, as shown in the supplied guide?

Yes, the locking lever assembly was correctly installed before I started to screw on the anti-vibration handle.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations confirm the locking lever assembly was in state 1 (correctly assembled) at frame 4715, prior to the start of the handle installation at frame 4785. The video visually confirms the lever is present on the device before the handle is picked up and screwed on. The answer correctly reflects this sequence and state.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__adapter_done__state_v10_2_0

Had I correctly installed the adapter plate by the end?

Yes, the adapter plate was correctly installed by the end of the segment.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the adapter plate is correctly assembled (state 1) at the end of the segment. The video visually confirms the operator completing the installation and fastening of the adapter plate, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__adapter_done__state_v10_2_1

Had I installed the gearbox housing before starting to attach the adapter plate, as shown in the supplied guide?

Yes, the gearbox housing was correctly installed before I started attaching the adapter plate.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source explicitly states the gearbox housing was in state 1 (correctly assembled) at the start of the adapter plate attachment step (frame 1152). The video visually confirms the housing is present and the operator proceeds to attach the adapter plate, consistent with the source and the guide's sequence.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_incomplete__state_v10_2_0

Had I correctly installed the bearing plate by the end?

No, the bearing plate was not correctly installed by the end.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["The video shows the operator inserting the bearing plate and manipulating it, but the final state (correctly seated vs. misaligned) is not visually resolvable from the provided frames due to occlusion and resolution. The 'misassembled' state relies entirely on the source annotation."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The answer is supported by the source annotation (state -1), but the visual evidence in the video is insufficient to independently confirm the 'misassembled' state. The operator is seen working on the component, but the specific failure mode or final incorrect position is not clearly visible.", "requested_evidence": ["Higher resolution view of the bearing plate interface at the end of the clip to visually confirm misalignment or incomplete seating."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_incomplete__state_v10_2_1

Had I installed the adapter plate before starting to insert the bearing plate assembly, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before I started inserting the bearing plate assembly.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source data (ASR state 6) confirms the adapter plate was in state 1 (correctly assembled) at frame 2535, which precedes the start of the bearing plate insertion action at frame 2647 (approx 88s). The video visually supports this sequence, showing the adapter plate installed before the user picks up and inserts the bearing plate. The answer correctly reflects this temporal order.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_done__state_v10_2_0

Had I correctly installed the bearing plate by the end?

Yes, the bearing plate was correctly installed by the end of the segment.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["Visibility of the bearing plate's final seated state is obstructed by the operator's hands and the angle of the gearbox housing in the final frames.", "The video shows the action of inserting and tightening, but the specific visual confirmation that the plate is flush and correctly seated is not clearly resolved in the provided frames."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The source annotations explicitly state the bearing plate is correctly assembled (state 1) at the end. However, the visual evidence in the video frames is insufficient to independently verify this state due to occlusion and resolution limits. The action is observed, but the final result is not clearly visible.", "requested_evidence": ["Clear view of the bearing plate flush against the gearbox housing without hand obstruction.", "Confirmation that the screws are fully tightened and the plate is not misaligned."], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__bearing_done__state_v10_2_1

Had I installed the adapter plate before starting to insert the bearing plate assembly, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before I started inserting the bearing plate assembly.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the adapter plate was in state 1 (correctly assembled) at frame 2535 (84.5s), which precedes the start of the bearing plate insertion action at 88.2s. The video visually confirms the adapter plate is attached to the gearbox housing before the operator begins handling the bearing plate assembly. The answer correctly reflects this sequence.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__handle_done__state_v10_2_0

Had I correctly installed the anti-vibration handle into the gearbox housing by the end?

Yes, the anti-vibration handle was correctly installed into the gearbox housing by the end.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations explicitly state the anti-vibration handle is correctly assembled (state 1) at the end of the segment. The video visually confirms the handle is attached to the gearbox housing at the end, consistent with the source claim.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_004_front__handle_done__state_v10_2_1

Had I installed the locking lever assembly before starting to screw on the anti-vibration handle, as shown in the supplied guide?

Yes, the locking lever assembly was correctly installed before I started to screw on the anti-vibration handle.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The source annotations confirm the locking lever assembly was in state 1 (installed) at frame 5268, prior to the handle installation starting at frame 5361. The video visually confirms the lever is present on the device before the handle is picked up and screwed on. The answer correctly reflects this sequence and state.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

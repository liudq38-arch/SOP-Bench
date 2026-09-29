# state_v10_smoke 开放题开发样本

1 个 front 装配视频；源标注辅助文本生成，视频单独核验；全部待真人审核。

```json
{
  "version": "state_v10_smoke",
  "events": 4,
  "videos": 1,
  "status": {
    "ok": 4
  },
  "qa_pairs": 8,
  "types": {
    "install_relation": 4,
    "reference_order": 4
  },
  "answer_polarities": {
    "yes": 7,
    "no": 1
  },
  "machine_decisions": {
    "keep_candidate": 7,
    "needs_evidence": 1
  },
  "structural_issue_pairs": 4,
  "deferred_types": {},
  "human_reviewed": 0,
  "limits": "Development only. Same-model screening is not accuracy. Illustrated sequence is not an exhaustive mandatory-order graph. All pending_human_review."
}
```

## AL07EJ17_Reassembly_A_002_front__adapter_done__state_v10_smoke_0

By the end of this segment, had I finished installing the adapter plate?

Yes, the adapter plate was correctly installed by the end of the video. The final state annotation confirms the adapter plate and its associated screws and nuts reached a correctly assembled state.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA question asks about the completion state of the adapter plate installation by the end of the segment. The source data (ASR state 6) explicitly marks the adapter plate and its fasteners as state 1 (correctly assembled) at the end of the interval. The video visually confirms the operator is working on the adapter plate throughout the segment and the final frames show the component attached to the gearbox housing, consistent with the 'completed' state annotation. The answer correctly reflects the source-supported final state.", "requested_evidence": [], "human_review_required": true}

结构检查：["unverified_receiver_relation"]

## AL07EJ17_Reassembly_A_002_front__adapter_done__state_v10_smoke_1

Did I install the rotor assembly before starting the adapter plate, as shown in the supplied guide?

Yes, the rotor assembly was installed before the adapter plate work began. The rotor components were in a correctly assembled state when the first action to attach the adapter plate started, matching the sequence shown in the official illustration.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA correctly identifies that the rotor assembly (gearbox housing, drive shaft, bevel gear) was in a completed state (state 1) prior to the start of the adapter plate attachment, consistent with the sequence shown in the official illustration. The video confirms the rotor assembly is installed and the operator proceeds to attach the adapter plate. The scope is explicitly limited to comparing the observed sequence with the supplied guide, which is valid.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_done__state_v10_smoke_0

By the end of this segment, had I finished installing the bearing plate assembly?

Yes, the bearing plate assembly was correctly installed by the end of the video. The final state annotation confirms the component reached a correctly assembled status after the insertion actions.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA question asks about the completion state of the bearing plate assembly at the end of the segment. The source data (ASR state 10) explicitly marks the 'bearing_plate' as state 1 (correctly assembled) at the end of the interval. The video visually confirms the operator inserting the plate and securing it with screws, resulting in a final state where the component is attached. The answer 'Yes' is supported by both the explicit state annotation and the visual evidence of the completed action.", "requested_evidence": [], "human_review_required": true}

结构检查：["unverified_receiver_relation"]

## AL07EJ17_Reassembly_A_002_front__bearing_done__state_v10_smoke_1

Did I install the adapter plate before starting the bearing plate assembly, as shown in the supplied guide?

Yes, the adapter plate was already correctly installed before I began inserting the bearing plate assembly. This sequence matches the order shown in the official reassembly illustration.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA correctly identifies that the adapter plate was installed (state 1) prior to the start of the bearing plate insertion (85.5s), consistent with the provided illustration's sequence. The source explicitly limits the order claim to a comparison with the guide, avoiding unwarranted normative assertions. Visual evidence confirms the adapter plate is present and secured before the bearing plate is handled.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__bearing_incomplete__state_v10_smoke_0

By the end of this segment, had I finished installing the bearing plate assembly?

No, the bearing plate assembly was not correctly installed by the end of the segment. The final state indicates the component is misassembled, and the top-left bearing screw remains unassembled.

自动审核：{"source_support": "supported", "visual_status": "uncertain", "source_issues": [], "visual_issues": ["Video resolution and lighting are insufficient to visually confirm the specific state of the 'top-left bearing screw' or the precise seating of the bearing plate assembly at the end of the clip.", "The operator is seen manipulating the bearing plate area, but the final state (misassembled vs. correctly seated) cannot be definitively verified visually without higher resolution or a different angle."], "question_scope_valid": true, "polarity_valid": true, "decision": "needs_evidence", "reason": "The QA answer is fully supported by the provided ASR state annotations (state -1 for bearing plate, state 0 for top-left screw). However, the visual evidence in the video is ambiguous due to low resolution and occlusion, making it impossible to independently verify the specific component states claimed in the answer. Expanded evidence (e.g., higher resolution frames or close-up views) is required to confirm the visual status.", "requested_evidence": ["High-resolution frames or a close-up view of the bearing plate assembly at the end of the segment (approx. 95s-96s) to verify the state of the top-left screw and plate seating."], "human_review_required": true}

结构检查：["unverified_receiver_relation"]

## AL07EJ17_Reassembly_A_002_front__bearing_incomplete__state_v10_smoke_1

Did I install the adapter plate before starting the bearing plate assembly, as shown in the supplied guide?

Yes, the adapter plate was correctly installed before the bearing plate assembly insertion began. This sequence matches the order shown in the official reassembly illustration.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA correctly identifies that the adapter plate was installed (state 1) before the bearing plate insertion began, consistent with the supplied guide's sequence. The source evidence (ASR states and action timestamps) supports the claim, and the video visually confirms the adapter plate is attached prior to the bearing plate handling.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

## AL07EJ17_Reassembly_A_002_front__handle_done__state_v10_smoke_0

By the end of this segment, had I finished installing the anti-vibration handle?

Yes, the anti-vibration handle was correctly installed by the end of the video. The final state annotation confirms the handle reached a correctly assembled state after the hand-tightening action.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA question asks about the completion state of the anti-vibration handle installation by the end of the segment. The source evidence (ASR state 14) explicitly marks the handle state as '1' (correctly assembled) at the end of the interval. The video visually confirms the operator performing the screwing action and the handle being attached to the tool at the end of the clip. The answer 'Yes' is supported by both the state annotation and the visual evidence.", "requested_evidence": [], "human_review_required": true}

结构检查：["unverified_receiver_relation"]

## AL07EJ17_Reassembly_A_002_front__handle_done__state_v10_smoke_1

Did I install the locking lever assembly before starting to screw on the anti-vibration handle, as shown in the supplied guide?

Yes, the locking lever assembly was installed before the anti-vibration handle was started. The state of the lever components was confirmed as correctly assembled at the moment the handle installation began, matching the sequence shown in the official illustration.

自动审核：{"source_support": "supported", "visual_status": "consistent", "source_issues": [], "visual_issues": [], "question_scope_valid": true, "polarity_valid": true, "decision": "keep_candidate", "reason": "The QA correctly identifies that the locking lever assembly was installed before the handle installation began, consistent with the sequence shown in the official manual illustration. The source data (ASR state 12) confirms the lever components were in state 1 (assembled) at the start of the handle action (160.8s). The video visually confirms the lever is present on the tool before the handle is picked up and screwed on. The scope is explicitly limited to comparing the observed sequence with the supplied guide, which is valid.", "requested_evidence": [], "human_review_required": true}

结构检查：[]

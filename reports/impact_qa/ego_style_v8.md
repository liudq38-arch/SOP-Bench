# EgoErrorVQA 风格开发对照 v8

原标注与研究代理目视描述辅助生成，全部待真人审核；自动 pass 不是准确率。

```json
{
  "events": 20,
  "status": {
    "ok": 20
  },
  "qa_pairs": 35,
  "decisions": {
    "pass": 27,
    "missing": 7,
    "revise": 1
  },
  "dimensions": {
    "corrective_action": 5,
    "correctness": 15,
    "placement": 5,
    "action": 7,
    "tool": 3
  },
  "structural_issue_events": 7,
  "human_reviewed": 0,
  "limits": "Development-only; supplied research-agent visual notes; same-model screening is not accuracy or human validation."
}
```

## NA07GE21_Reassembly_A_001_ego__left__0049__v8_0

What corrective action am I performing with my left hand?

I am picking up an M4 nut from the work surface and moving it toward the assembly held in my right hand.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video clearly shows the left hand picking up a small component (nut) from the work surface and moving it towards the assembly held in the right hand. This visual evidence supports the answer and the annotation's description of the action and hand usage."
  }
}
```

## SS07EL13_Reassembly_A_001_ego__right__0132__v8_0

What corrective action am I performing with my right hand?

I am loosening a screw as part of a recovery step. I am manipulating the screw with my fingertips near the housing.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video shows the right hand manipulating a screw on the device housing with fingertips, consistent with the 'loosen_screw' action and 'recovery' phase. The visual note regarding manipulation near the housing is supported by the visible hand position."
  }
}
```

## MA07LF04_Disassembly_A_001_ego__left__0110__v8_0

What corrective action am I performing with my left hand?

I am pinching and adjusting the component with my left fingertips as part of a recovery step.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.phase",
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video clearly shows the left hand pinching and adjusting the component on the tool, which aligns with the source label 'hand_loosen_M4_nut' and the visual note 'pinched and adjusted it with my left fingertips.' The action is visible and specific to the task."
  }
}
```

## MA07LF04_Reassembly_A_001_ego__left__0134__v8_0

What corrective action is being performed with the left hand?

The left hand is attaching a lever near the junction between the metal shaft and the black housing.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The QA correctly identifies the left hand performing an attachment action near the junction of the shaft and housing, consistent with the visual evidence and source labels. The 'recovery' phase is supported by the source annotation and does not require visual confirmation of the error mechanism."
  }
}
```

## MA07LF04_Disassembly_A_003_ego__right__0088__v8_0

What corrective action am I performing with my right hand?

I am lifting a small part from the work surface as part of a recovery step.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.phase",
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video shows the right hand lifting a small component from the work surface, which aligns with the source label 'pick_up_screw' and the visual note 'I lifted a small part'. The action is clearly visible and supported by the frames."
  }
}
```

## MA07LF04_Reassembly_B_005_ego__left__0101__v8_0

Is the action of dismounting the adapter plate with my left hand performed correctly?

No, the action is anomalous due to issues with timing, placement, handling, and procedure.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source annotation regarding the anomalous nature of the action (timing, placement, handling, procedure). The video shows the user handling the motor assembly, which aligns with the context of the task, though the specific 'adapter plate' mentioned in the source is not clearly distinguishable in the provided frames. Since the answer relies on the source label for the anomaly classification, it is accepted as aligned."
  }
}
```

## MA07LF04_Reassembly_B_005_ego__left__0101__v8_1

Where did I place the adapter plate after dismounting it?

I put it on the work surface to the left of the metal assembly.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer states the object was placed to the left of the metal assembly. The video frames (specifically 00:01-00:07) clearly show a black ring-shaped component (the adapter plate) resting on the work surface to the left of the main motor assembly. This visual evidence supports the claim made in the answer."
  }
}
```

## SS07EL13_Disassembly_A_002_ego__right__0051__v8_0

Is the action of loosening the screw with my right hand performed correctly?

No, the action is anomalous due to issues with timing, handling, and tool selection.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source annotation (phase: anomaly; anomaly_types: temporal, handling, wrong_tool). The video shows the right hand manipulating the component, but the specific claim of 'repeatedly adjusted it with my fingertips' is not visually verifiable in the sampled frames; therefore visual_detail_supported is false. No contradictions or unsupported causal claims are present."
  }
}
```

## SS07EL13_Disassembly_A_002_ego__right__0051__v8_1

What specific physical adjustment did I make to the screw?

I repeatedly adjusted it with my fingertips.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {}
}
```

## LE07UF17_Reassembly_A_002_ego__left__0018__v8_0

Is the action of holding the gearbox housing with the opening facing upward performed correctly in this step?

No, this action is flagged as an anomaly due to issues with timing, part selection, and procedure. The visual evidence confirms the housing was held with the opening facing upward.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly identifies the action as an anomaly based on the provided source labels (temporal, wrong_part, procedural). The visual detail regarding the left hand holding the housing with the opening facing upward is supported by the video frames (e.g., 00:00-00:04, 00:09-00:13), where the housing is clearly held in that orientation."
  }
}
```

## LE07UF17_Reassembly_A_002_ego__left__0018__v8_1

What specific action is my left hand performing with the gearbox housing?

My left hand is supporting the housing with its opening facing upward.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer accurately describes the specific action of the left hand as seen in the video. The visual evidence confirms the left hand is supporting the gearbox housing with the opening facing upward, aligning with the visual note and source fields."
  }
}
```

## LE06AS03_Reassembly_A_002_ego__right__0208__v8_0

Is the action of holding the Torx screwdriver performed correctly in this step?

No, the action is flagged as anomalous due to issues with timing, location, and procedure.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source labels (phase: anomaly, anomaly_types: temporal, spatial, procedural). It does not invent a causal mechanism or claim a specific physical error, but rather reports the classification provided in the source. No concrete visual claim is made in the answer that requires independent visual confirmation beyond the label."
  }
}
```

## LE06AS03_Reassembly_A_002_ego__right__0208__v8_1

Where is the right hand holding the Torx screwdriver?

The hand is holding the screwdriver above the printed instructions on the work surface.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer states the hand is holding the screwdriver above the printed instructions. This is visually supported by the video frames, where the right hand is clearly positioned over the instruction sheet while holding the tool."
  }
}
```

## KJ03JM25_Disassembly_A_003_ego__right__0028__v8_0

Is the action of picking up the small metal part with my right hand performed correctly?

No, this action is flagged as anomalous due to issues with timing, location, and handling.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types",
    "annotation.hand",
    "annotation.action"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source labels (phase: anomaly, anomaly_types: temporal/spatial/handling, hand: right, action: pick_up_screw). The video shows the right hand interacting with a small metal part on the mat, supporting the visual claim. No contradictions or invented mechanisms are present."
  }
}
```

## KJ03JM25_Disassembly_A_003_ego__right__0028__v8_1

What specific object did I pick up with my right hand?

I picked up a small metal part.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer",
    "annotation.hand"
  ],
  "review": {}
}
```

## LE06AS03_Reassembly_A_004_ego__right__0080__v8_0

Is the placement of the bevel gear by my right hand correct?

No, the placement is incorrect because the part is being placed on the work surface instead of into the assembly.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video shows the right hand placing a small black component (identified as the bevel gear in the source) onto the work surface rather than into the assembly held in the left hand. This visual evidence supports the source label 'wrong_part' and the answer stating the placement is incorrect because it is on the surface."
  }
}
```

## LE06AS03_Reassembly_A_004_ego__right__0080__v8_1

Where is the bevel gear located during this action?

The bevel gear is placed on the work surface beside the assembly held in my left hand.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video clearly depicts the bevel gear resting on the grey work surface next to the assembly held in the left hand. This confirms the answer provided in the QA pair."
  }
}
```

## TO08CO25_Disassembly_B_005_ego__left__0009__v8_0

Is the action of picking up the screwdriver performed correctly?

No, the action is anomalous because the wrong tool is being selected and the spatial handling is incorrect.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video clearly shows the left hand picking up the orange and yellow handled screwdriver. The annotation correctly identifies the hand, the tool, and the phase as anomalous (wrong tool). The answer accurately reflects the visual evidence and the source labels."
  }
}
```

## TO08CO25_Disassembly_B_005_ego__left__0009__v8_1

What specific tool is being picked up by the left hand?

The left hand is picking up an orange and yellow handled screwdriver.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {}
}
```

## MA07LF04_Disassembly_B_005_ego__left__0044__v8_0

Is the action of spinning the drive shaft with the left hand performed correctly?

No, the action is flagged as anomalous due to issues with timing, location, and handling.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types",
    "annotation.hand",
    "annotation.action"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source labels (phase: anomaly, anomaly_types: temporal/spatial/handling, hand: left, action: hand_spin_drive_shaft). It does not invent mechanisms or claim recovery. Visual detail is not independently confirmed in the provided frames, so visual_detail_supported is false, but this does not require rejection per instructions."
  }
}
```

## MA07LF04_Disassembly_B_005_ego__left__0044__v8_1

What specific component is being manipulated during this step?

The operator is manipulating the gray toothed wheel.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {}
}
```

## LE06AS03_Reassembly_B_005_ego__right__0174__v8_0

Is the action of inserting the bevel gear into the housing performed correctly?

No, the action is incorrect because the wrong part is being used and the procedure is flawed.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types"
  ],
  "review": {
    "qa_index": 0,
    "decision": "revise",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The claim that the 'wrong part' is being used cannot be visually confirmed from the provided frames; the specific identity of the part is ambiguous.",
      "The claim that the 'procedure is flawed' is a judgment based on the source label, not a visible contradiction in the video itself."
    ],
    "reason": "The answer asserts specific error mechanisms ('wrong part', 'flawed procedure') that are not visually verifiable in the target video. The video shows a part being inserted, but without external context or a clear visual mismatch (e.g., obvious size difference), the 'wrong part' claim is unsupported by the visual evidence alone. The answer relies entirely on the source label's classification rather than independent visual confirmation."
  }
}
```

## LE06AS03_Reassembly_B_005_ego__right__0174__v8_1

Where am I inserting the part with my right hand?

I am inserting the part into the opening of the metal housing held in my left hand.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly describes the visible action: the right hand is inserting a part into the opening of the metal housing held by the left hand. This is clearly supported by the video frames."
  }
}
```

## LE06AS03_Reassembly_A_001_ego__right__0346__v8_0

Is the action of placing the Torx screwdriver performed correctly in this step?

No, the action is flagged as anomalous due to issues with timing, location, and procedure. The operator is moving the tool toward the instruction sheet rather than the assembly.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly identifies the action as anomalous based on the provided labels (temporal, spatial, procedural) and aligns with the visual evidence showing the tool moving toward the instruction sheet rather than the assembly."
  }
}
```

## LE06AS03_Reassembly_A_001_ego__right__0346__v8_1

Where is the Torx screwdriver being directed during this action?

The screwdriver is being moved from above the assembly toward the printed instruction sheet.

```json
{
  "phase": "anomaly",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer accurately describes the direction of the screwdriver movement as seen in the video frames, supported by the visual note."
  }
}
```

## KI05KO01_Disassembly_A_002_ego__right__0084__v8_0

Was the action of removing the bearing plate performed correctly?

Yes, the extraction of the bearing plate was executed as a normal step without anomalies.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.phase",
    "annotation.anomaly_types"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source annotation (phase: normal, no anomalies). It does not make unsupported visual claims; the visual note is not required to be independently verified for this correctness judgment."
  }
}
```

## KI05KO01_Disassembly_A_002_ego__right__0084__v8_1

How did I remove the bearing plate from the body?

I grasped the edge of the plate with my fingers and pulled it away from the body held in my left hand.

```json
{
  "phase": "normal",
  "sources": [
    "visual_note.answer"
  ],
  "review": {}
}
```

## KI03AR28_Disassembly_A_004_ego__right__0090__v8_0

Is the action of picking up the screwdriver performed correctly in this step?

Yes, the action is performed correctly as part of the normal disassembly phase. The right hand successfully picks up the orange-handled screwdriver.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.phase",
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video clearly shows the right hand reaching for and grasping an orange-handled screwdriver. This aligns with the annotation 'pick_up_phillips_screwdriver' and the visual note. The action is part of the disassembly process shown in the context of the workspace."
  }
}
```

## KI03AR28_Disassembly_A_004_ego__right__0090__v8_1

What tool is being picked up by the right hand?

The right hand is picking up an orange-handled screwdriver.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {}
}
```

## KI03AR28_Disassembly_A_002_ego__right__0070__v8_0

Is the action of aligning the screw with the right hand performed correctly in this step?

Yes, the alignment action is performed correctly as indicated by the normal phase. The shaft is oriented downward toward the component during the operation.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video confirms the right hand is holding the tool with the shaft oriented downward toward the component, aligning with the 'align_screw' action and 'normal' phase. The visual evidence supports the claim that the shaft is pointed downward."
  }
}
```

## KI03AR28_Disassembly_A_002_ego__right__0070__v8_1

What is the orientation of the tool shaft while aligning the screw?

The shaft is pointed downward toward the component.

```json
{
  "phase": "normal",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video clearly shows the tool shaft pointing downward toward the component being worked on, which directly supports the answer provided."
  }
}
```

## ER10WE06_Reassembly_A_004_ego__right__0059__v8_0

Is the action of attaching the screw with the right hand performed correctly in this step?

Yes, the action is performed correctly as indicated by the normal phase annotation. The operator is using an orange-handled screwdriver to attach the screw.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.phase",
    "annotation.action",
    "annotation.hand",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The video shows the right hand using an orange-handled screwdriver to work on the object, which aligns with the annotation 'attach_screw' and 'normal' phase. The visual note correctly identifies the tool. The answer correctly attributes the 'correctness' judgment to the source annotation while confirming the visible tool details."
  }
}
```

## ER10WE06_Reassembly_A_004_ego__right__0059__v8_1

What tool is being used to attach the screw?

An orange-handled screwdriver is being used.

```json
{
  "phase": "normal",
  "sources": [
    "visual_note.answer"
  ],
  "review": {}
}
```

## NA07GE21_Disassembly_A_002_ego__left__0038__v8_0

Is the action of extracting the drive shaft with the left hand performed correctly in this step?

Yes, the extraction of the drive shaft using the left hand is performed correctly as part of the normal disassembly phase.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase"
  ],
  "review": {
    "qa_index": 0,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer correctly reflects the source labels (action, hand, phase) without inventing visual evidence. The video shows the left hand holding the shaft assembly while the right hand manipulates the housing, consistent with the 'extract_drive_shaft' action. No visual contradiction exists."
  }
}
```

## NA07GE21_Disassembly_A_002_ego__left__0038__v8_1

What specific component is being handled during this action?

The metal shaft assembly is being handled during this extraction step.

```json
{
  "phase": "normal",
  "sources": [
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 1,
    "decision": "pass",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [],
    "reason": "The answer identifies the 'metal shaft assembly', which is clearly visible in the video frames held by the left hand. The visual evidence supports the specific component claim."
  }
}
```

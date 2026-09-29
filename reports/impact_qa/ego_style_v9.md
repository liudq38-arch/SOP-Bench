# EgoErrorVQA 风格开发对照 v9

原标注与研究代理目视描述辅助生成，全部待真人审核；自动 pass 不是准确率。

```json
{
  "events": 20,
  "status": {
    "ok": 20
  },
  "qa_pairs": 20,
  "decisions": {
    "revise": 3,
    "reject": 14,
    "pass": 3
  },
  "dimensions": {
    "corrective_action": 4,
    "correctness": 6,
    "error_description": 10
  },
  "structural_issue_events": 0,
  "human_reviewed": 0,
  "limits": "Development-only; supplied research-agent visual notes; same-model screening is not accuracy or human validation."
}
```

## NA07GE21_Reassembly_A_001_ego__left__0049__v9_0

What corrective action did I perform with my left hand?

I picked up the small part from the work surface and moved it toward the assembly held in my right hand.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "revise",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [
      "corrective action"
    ],
    "reason": "The visual evidence confirms the left hand picks up a small part and moves it toward the assembly. However, the question asks for a 'corrective action'. While the annotation labels the phase as 'recovery', the video frames alone do not visually demonstrate that an error occurred or that this specific movement was a correction of a mistake. Labeling the action as 'corrective' relies on the annotation's interpretation rather than direct visual confirmation of an error being fixed. The question should be rephrased to ask about the physical action performed rather than its normative status as a correction."
  }
}
```

## SS07EL13_Reassembly_A_001_ego__right__0132__v9_0

What corrective action did I perform with my right hand near the housing?

I manipulated the small part near the housing with my fingertips.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer claims the user 'manipulated the small part near the housing with my fingertips', but the video frames show the right hand gripping and turning the large black housing body itself, not a separate small part.",
      "The question asks for a 'corrective action', implying a recovery from an error. The video shows a standard assembly motion (tightening or loosening the housing) without any visible evidence of a prior error or a specific recovery mechanism."
    ],
    "reason": "The visual evidence contradicts the specific details in the answer. The video shows the right hand manipulating the main housing unit, not a 'small part' near it. Additionally, the question frames the action as 'corrective' based on the annotation's 'recovery' phase, but the video does not visually support the existence of an error or a specific recovery process, making the 'corrective' claim unsupported by the visual data."
  }
}
```

## MA07LF04_Disassembly_A_001_ego__left__0110__v9_0

What corrective action did I perform on the small part near the shaft?

I pinched and adjusted the small part near the shaft with my left fingertips.

```json
{
  "phase": "recovery",
  "sources": [
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "revise",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [
      "corrective action"
    ],
    "reason": "The visual evidence supports the physical description of pinching and adjusting the small part with the left fingertips. However, the question and answer frame this as a 'corrective action.' The video shows the user manipulating the part, but there is no visible evidence of a prior error or a specific correction being performed (e.g., fixing a misalignment or re-seating a loose part). The 'recovery' phase label in the annotation is not visually substantiated by the action itself in this short clip. Therefore, the normative claim of 'corrective action' is unsupported by the visual data."
  }
}
```

## MA07LF04_Reassembly_A_001_ego__left__0134__v9_0

Did I correctly attach the lever with my left hand?

I used my left hand to attach the lever, with my fingertips contacting the assembly near the junction between the metal shaft and the black housing.

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
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts that the lever was attached, but the video frames show the hands holding the assembly in a static position without any visible motion of insertion or locking.",
      "The answer claims the fingertips contacted the junction between the metal shaft and the black housing, but the visual evidence shows the left hand gripping the side of the black housing, not the shaft junction."
    ],
    "reason": "The QA pair fails because the answer makes unsupported claims about the completion of the action ('attached the lever') and the specific contact point ('junction between the metal shaft and the black housing'). The video shows the hands holding the assembly, but does not show the lever being inserted or the fingers touching the shaft junction. The answer invents a successful completion and a specific physical interaction that are not visible in the provided frames."
  }
}
```

## MA07LF04_Disassembly_A_003_ego__right__0088__v9_0

What corrective action did I perform with my right hand near the black circular part?

I lifted a small part from the work surface.

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
    "decision": "revise",
    "annotation_alignment": true,
    "visual_detail_supported": true,
    "task_relevant": true,
    "unsupported_details": [
      "corrective action"
    ],
    "reason": "The question asks for a 'corrective action', which implies a normative judgment that the action was fixing an error. While the annotation labels the phase as 'recovery', the visual evidence only confirms the physical act of lifting a small part. The video does not provide a visible mechanism or context to confirm that this specific lift was a correction of a prior mistake (e.g., dropping a part) versus a standard step in the process. Therefore, the term 'corrective action' is an unsupported normative claim. The question should be revised to ask about the physical action performed (e.g., 'What did I do with my right hand...') rather than the intent or classification of the action."
  }
}
```

## MA07LF04_Reassembly_B_005_ego__left__0101__v9_0

Did I perform the action of dismounting the adapter plate correctly?

No, I did not perform the action correctly. While I used my left hand to remove the black circular piece and placed it on the work surface to the left of the metal assembly, the operation was flagged as anomalous due to issues with timing, placement, handling, and procedure.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "claim that the action was performed incorrectly",
      "assertion of specific anomaly types (timing, placement, handling, procedure) without visible evidence",
      "use of the term 'flagged' which is not a natural observation"
    ],
    "reason": "The answer asserts that the action was performed incorrectly and lists specific anomaly types (timing, placement, handling, procedure). However, the video only shows the user removing a black circular piece and placing it on the table. There is no visual evidence in the provided frames to support claims of incorrect timing, improper placement, or procedural errors. The answer relies entirely on the annotation's 'anomaly' label rather than observable physical facts. Additionally, the use of the word 'flagged' violates the instruction to avoid annotation-specific terminology."
  }
}
```

## SS07EL13_Disassembly_A_002_ego__right__0051__v9_0

Did I correctly loosen the screw with my right hand?

No, I used the wrong tool and handled the part incorrectly, repeatedly adjusting it with my fingertips instead of properly loosening the screw.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "used the wrong tool",
      "handled the part incorrectly",
      "repeatedly adjusting it with my fingertips"
    ],
    "reason": "The answer asserts specific error mechanisms ('wrong tool', 'handled incorrectly', 'repeatedly adjusting') that are not visually supported by the video. The video shows the right hand holding a screwdriver and manipulating a small part inside the housing, but it does not clearly demonstrate that the tool is wrong for the task, nor does it show the specific 'repeated adjusting' motion described. The claim of 'wrong tool' is a normative judgment not evidenced by the visual data (the tool appears to be a screwdriver, which is plausible for the action). The claim of 'repeatedly adjusting' is an interpretation of the motion that is not definitively visible in the sampled frames. Therefore, the visual details in the answer are unsupported."
  }
}
```

## LE07UF17_Reassembly_A_002_ego__left__0018__v9_0

Did I perform the action of holding the gearbox housing drive shaft correctly with my left hand?

No, I did not perform this action correctly. While my left hand supported the housing with its opening facing upward, this step involved using the wrong part, occurred at the wrong time, and followed an incorrect procedure.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts the action was performed incorrectly due to 'wrong part', 'wrong time', and 'incorrect procedure', but the video only shows the left hand holding the housing. There is no visual evidence of a wrong part being used, a temporal error, or a procedural deviation in the holding action itself.",
      "The claim that the step 'involved using the wrong part' is not supported by the visual evidence; the video shows the housing being held, but does not confirm if the part inside or the housing itself is the 'wrong' one for the specific step, nor does it show an insertion failure.",
      "The claim of 'wrong time' and 'incorrect procedure' are normative judgments not visible in the clip. The video shows the hand holding the object, which is a valid physical action, but the video does not provide the context to verify if this timing or procedure is actually erroneous."
    ],
    "reason": "The QA pair makes strong normative claims about the correctness of the action ('wrong part', 'wrong time', 'incorrect procedure') that are not supported by the visual evidence in the video. The video only shows the left hand holding the gearbox housing. While the annotation flags an anomaly, the video does not visually confirm the specific nature of the error (e.g., it doesn't show a wrong part being inserted or a clear procedural violation in the holding action). The answer treats the annotation's abstract labels as visible facts, which violates the requirement to verify concrete physical claims against the video."
  }
}
```

## LE06AS03_Reassembly_A_002_ego__right__0208__v9_0

Did I hold the Torx screwdriver correctly during this step?

No, I held the screwdriver tip above the printed instructions on the work surface instead of using it on the tool.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
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
    "reason": "The QA pair correctly identifies the anomaly where the user holds the screwdriver tip above the printed instructions rather than engaging it with the tool. The visual evidence in the frames (e.g., 390.617s, 393.185s) clearly shows the right hand holding the screwdriver over the paper diagram, supporting the claim that the tool was not being used on the device. The answer accurately reflects the visual observation without making unsupported normative claims about the correct procedure."
  }
}
```

## KJ03JM25_Disassembly_A_003_ego__right__0028__v9_0

Did I pick up the correct part from the mat with my right hand at the right time and with proper handling?

No, I picked up a small metal part, but the timing, location, or how I handled it was incorrect.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts that the timing, location, or handling was incorrect, but the video frames only show the action of picking up the part. There is no visual evidence in the provided frames to confirm a temporal, spatial, or handling error."
    ],
    "reason": "The QA pair claims specific errors (timing, location, handling) based on the annotation labels, but the video evidence does not support these specific claims. The frames show the user picking up a small metal part, but without a reference for the 'correct' time, place, or grip, the assertion that the action was performed incorrectly is unsupported by the visual data. The answer relies on the annotation's classification rather than observable physical evidence of an error."
  }
}
```

## LE06AS03_Reassembly_A_004_ego__right__0080__v9_0

Did I place the bevel gear correctly with my right hand?

No, I placed the wrong part on the work surface beside the assembly I was holding in my left hand instead of installing it.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "Identifying the object as a 'bevel gear' is not visually verifiable from the provided frames.",
      "Asserting the part was 'wrong' or 'not installed' relies on the annotation label rather than visual evidence of a failed attempt or a specific required destination."
    ],
    "reason": "The answer makes specific claims about the object identity ('bevel gear') and the normative correctness ('wrong part', 'instead of installing it') that are not supported by the visual evidence. The video shows a small black object being placed on the table, but it is too small and indistinct to confirm it is a bevel gear. Furthermore, the video does not show an attempt to install the part into the assembly, so the claim that it was placed 'instead of installing it' is an inference based on the annotation, not a visual observation. The answer should be limited to describing the visible action (placing a small part on the table) without asserting the specific part name or the intent to install."
  }
}
```

## TO08CO25_Disassembly_B_005_ego__left__0009__v9_0

Did I pick up the correct tool with my left hand?

No, I picked up an orange and yellow handled screwdriver, which is the wrong tool for this step.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts the tool is 'wrong' for the step, but the video only shows the tool being picked up; it does not show the intended use or the correct tool, so the normative claim of error is unsupported by the visual evidence."
    ],
    "reason": "The QA pair claims the tool picked up is the 'wrong tool'. While the video confirms the user picked up an orange and yellow handled screwdriver, it does not provide visual evidence of what the 'correct' tool should be or that the action was an error in the context of the task. The assertion of 'wrongness' relies on external knowledge or the annotation label rather than the visual content of the video itself, violating the requirement to verify concrete physical claims against the video."
  }
}
```

## MA07LF04_Disassembly_B_005_ego__left__0044__v9_0

Did I correctly spin the drive shaft with my left hand?

No, I manipulated the gray toothed wheel at the end of the shaft, but the action was flagged as anomalous due to issues with timing, position, and handling.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer claims the action was 'flagged as anomalous due to issues with timing, position, and handling', but the video frames show no visible evidence of timing errors, spatial misplacement, or improper handling force. The left hand is simply holding and rotating the gray toothed wheel attached to the shaft; there is no visual mechanism to support the specific anomaly types listed.",
      "The question asks if the user 'correctly' spun the shaft, implying a normative judgment of success/failure. The video only shows the physical manipulation of the part. Without a visible failure mechanism (e.g., the part falling off, jamming, or being placed in the wrong location), the assertion of incorrectness is unsupported by the visual evidence."
    ],
    "reason": "The QA pair relies on annotation metadata ('flagged as anomalous') to assert specific error types (timing, position, handling) that are not visually verifiable in the provided frames. The video shows the left hand manipulating the gray toothed wheel, but does not demonstrate the specific errors claimed in the answer. Additionally, the question asks for a normative judgment ('correctly') which cannot be answered based solely on the visual evidence of the action itself without external context or visible failure."
  }
}
```

## LE06AS03_Reassembly_B_005_ego__right__0174__v9_0

Did I correctly insert the bevel gear into the metal housing with my right hand?

No, I inserted the wrong part into the opening of the metal housing held in my left hand.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.anomaly_types",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts that the 'wrong part' was inserted. While the video shows a small dark component being placed into the housing, there is no visual evidence within the clip to confirm that this specific component is the 'wrong part' or that it is not the bevel gear. The claim of error relies entirely on the annotation label rather than visible physical characteristics or a failed fit."
    ],
    "reason": "The QA pair claims the user inserted the 'wrong part'. However, the video only shows the insertion of a small dark component. Without visual confirmation of a mismatch (e.g., the part not fitting, or a clear visual distinction from the expected bevel gear), the assertion that it is the 'wrong part' is an unsupported normative claim derived solely from the annotation, violating the instruction to not treat placement as evidence of error without a visible mechanism."
  }
}
```

## LE06AS03_Reassembly_A_001_ego__right__0346__v9_0

Did I place the Torx screwdriver correctly during this step?

No, I moved the screwdriver with my right hand from above the assembly toward the printed instruction sheet instead of placing it on the workpiece.

```json
{
  "phase": "anomaly",
  "sources": [
    "annotation.action",
    "annotation.hand",
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
    "reason": "The QA pair accurately reflects the visual evidence in the target interval. The video shows the right hand moving the screwdriver away from the assembly and pointing it at the instruction sheet (specifically 'Schritt 3'), rather than using it on the workpiece. The answer correctly describes this movement and identifies it as an error relative to the task of reassembly, aligning with the 'anomaly' phase and 'temporal/spatial' attributes in the annotation. The question is natural and avoids forbidden terminology."
  }
}
```

## KI05KO01_Disassembly_A_002_ego__right__0084__v9_0

Did I correctly separate the black circular piece from the body using my right hand?

Yes, I grasped the edge of the black circular piece with my right fingers and pulled it away from the body held in my left hand.

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
    "reason": "The video frames confirm the right hand grasping the edge of the black circular component and pulling it away from the main body held in the left hand. The action aligns with the 'extract_bearing_plate' label and the 'normal' phase. The visual evidence supports the specific physical claims made in the answer regarding the separation method."
  }
}
```

## KI03AR28_Disassembly_A_004_ego__right__0090__v9_0

Did I correctly pick up the tool with my right hand to proceed with the disassembly?

Yes, I picked up an orange-handled screwdriver with my right hand.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts the action was 'correct' to proceed with disassembly, but the video only shows the tool being picked up; it does not show the tool being used or the disassembly proceeding, so the correctness claim is unsupported.",
      "The answer claims the screwdriver is 'orange-handled', but the video shows a screwdriver with a black handle and an orange tip/insert; the description is inaccurate."
    ],
    "reason": "The QA pair fails on two counts. First, the answer makes a normative claim ('correctly... to proceed') that cannot be verified from the visual evidence, which only shows the pickup action, not the subsequent successful use. Second, the visual detail describing the tool as 'orange-handled' contradicts the video, where the handle is clearly black with an orange accent. The instructions require rejecting pairs with direct contradictions or invented required actions."
  }
}
```

## KI03AR28_Disassembly_A_002_ego__right__0070__v9_0

Did I correctly align the screw with the screwdriver in my right hand?

Yes, I aligned the screw by holding the screwdriver in my right hand with its shaft pointing downward toward the component.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts that the screw was 'aligned' with the screwdriver. The video frames show the screwdriver tip positioned near the screw head, but the specific action of 'aligning' (engaging the tip into the screw slot) is not visually confirmed. The screwdriver appears to be hovering or just touching the surface, not clearly engaged for turning.",
      "The answer claims the shaft was pointing 'downward toward the component'. While the general orientation is downward, the specific alignment required for the action 'align_screw' is not definitively visible in the provided frames."
    ],
    "reason": "The QA pair asserts a successful alignment ('Yes, I aligned the screw') which is not visually supported by the frames. The frames show the screwdriver approaching or touching the screw, but do not confirm the tip is engaged in the screw head. The visual evidence is ambiguous regarding the completion of the 'align' action, making the affirmative answer unsupported."
  }
}
```

## ER10WE06_Reassembly_A_004_ego__right__0059__v9_0

Did I correctly attach the screw using the tool in my right hand?

Yes, I attached the screw using an orange-handled screwdriver held in my right hand.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts that the screw was attached, but the video frames only show the hand holding the screwdriver and positioning it; the actual insertion or tightening of the screw is not visible in the provided interval."
    ],
    "reason": "The QA pair claims the screw was 'attached' (completed action), but the visual evidence in the target interval (71.3s-72.7s) only shows the preparation phase where the screwdriver is held and positioned. The mechanism of attachment (turning the screw, screw entering the hole) is not visible. Asserting completion based on the tool being held violates the requirement to verify concrete physical claims against the video."
  }
}
```

## NA07GE21_Disassembly_A_002_ego__left__0038__v9_0

Did I correctly extract the drive shaft with my left hand while pulling the housing away?

Yes, I used my left hand to support the metal shaft assembly while my right hand pulled the housing away to extract the drive shaft.

```json
{
  "phase": "normal",
  "sources": [
    "annotation.action",
    "annotation.hand",
    "annotation.phase",
    "visual_note.answer"
  ],
  "review": {
    "qa_index": 0,
    "decision": "reject",
    "annotation_alignment": true,
    "visual_detail_supported": false,
    "task_relevant": true,
    "unsupported_details": [
      "The answer asserts 'correctly' extracted the drive shaft, but the video frames only show the hands holding the separated components; the actual extraction motion or completion is not visible in the provided interval.",
      "The claim that the left hand 'supported' the shaft while the right 'pulled' implies a specific causal mechanism of extraction that is not visually confirmed in the static frames provided, which show the parts already separated or being held apart."
    ],
    "reason": "The QA pair makes a normative claim ('correctly') and asserts a completed action ('extracted') that cannot be visually verified from the provided frames. The frames show the components separated, but do not show the extraction process itself, nor do they confirm the specific hand roles (supporting vs pulling) during the extraction event. The answer relies on the annotation's label rather than visible evidence of the action's success or mechanics."
  }
}
```

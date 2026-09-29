# development v1 自动审核



{"ok": 20, "structural_issue_events": 6, "refined_events": 1, "conflict_events": 3, "strict_machine_pass": 14}



{"pass": 23, "revise": 7, "reject": 10}



Same-model independent-call audit; not human accuracy, not independent-model verification.



## ER10WE06_Reassembly_A_004_ego__right__0059 / 0

{
  "event_id": "ER10WE06_Reassembly_A_004_ego__right__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did I grasp with my right hand to perform the attach_screw action?",
  "answer": "I grasped an orange-handled screwdriver.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F7:visual_without_observation",
    "fact:F8:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## ER10WE06_Reassembly_A_004_ego__right__0059 / 1

{
  "event_id": "ER10WE06_Reassembly_A_004_ego__right__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "How did I position the screwdriver relative to the component held by my left hand?",
  "answer": "I positioned the tip of the screwdriver against the black component while maintaining contact.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F7:visual_without_observation",
    "fact:F8:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_002_ego__right__0070 / 0

{
  "event_id": "KI03AR28_Disassembly_A_002_ego__right__0070",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did I hold in my right hand while aligning the screw?",
  "answer": "I held a green-handled screwdriver.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## KI03AR28_Disassembly_A_002_ego__right__0070 / 1

{
  "event_id": "KI03AR28_Disassembly_A_002_ego__right__0070",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did I perform the align_screw action with my right hand without any recorded anomalies?",
  "answer": "Yes, the annotated phase for the right hand's align_screw action is normal with no anomaly types recorded.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks about annotation metadata (phase/anomaly status) rather than visual evidence. While the answer is factually correct based on the provided JSON, it is not visually answerable from the frames alone."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_004_ego__right__0090 / 0

{
  "event_id": "KI03AR28_Disassembly_A_004_ego__right__0090",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do with the orange-handled tool on the work surface?",
  "answer": "My right hand reached for, grasped, and lifted the orange-handled tool off the work surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## KI03AR28_Disassembly_A_004_ego__right__0090 / 1

{
  "event_id": "KI03AR28_Disassembly_A_004_ego__right__0090",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did my right hand perform the pick-up action without any anomalies?",
  "answer": "Yes, the annotation classifies the phase of the pick-up action as normal with no anomaly types listed.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question relies entirely on annotation metadata (phase/anomaly_types) rather than visual evidence, which is weak for an anomaly-understanding dataset."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI05KO01_Disassembly_A_002_ego__right__0084 / 0

{
  "event_id": "KI05KO01_Disassembly_A_002_ego__right__0084",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did I use with my right hand to assist in extracting the bearing plate?",
  "answer": "I used a black-handled screwdriver, inserting it into a slot on the component and rotating the handle.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## KI05KO01_Disassembly_A_002_ego__right__0084 / 1

{
  "event_id": "KI05KO01_Disassembly_A_002_ego__right__0084",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did I encounter an anomaly while performing the target action of extracting the bearing plate?",
  "answer": "No, the annotated phase for the target action is 'normal' with no anomaly types listed, although a preceding action was marked as an anomaly.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question relies entirely on the 'phase' annotation label rather than visual evidence of an anomaly or lack thereof. While the answer is factually correct based on the provided metadata, it fails the criterion for an open-ended anomaly-understanding dataset where questions should probe visual reasoning."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KJ03JM25_Disassembly_A_003_ego__right__0028 / 0

{
  "event_id": "KJ03JM25_Disassembly_A_003_ego__right__0028",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "handling"
  ],
  "qa_index": 0,
  "question": "What did my right hand do with the screw after picking it up from the work surface?",
  "answer": "I moved the screw towards and placed it into the orange bin labeled 'Box 2'.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## KJ03JM25_Disassembly_A_003_ego__right__0028 / 1

{
  "event_id": "KJ03JM25_Disassembly_A_003_ego__right__0028",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "handling"
  ],
  "qa_index": 1,
  "question": "How is the action of my right hand picking up the screw characterized in the annotation?",
  "answer": "The action is annotated as an anomaly involving temporal, spatial, and handling issues.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for annotation metadata rather than visual evidence; weak for anomaly understanding dataset."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE06AS03_Reassembly_A_001_ego__right__0346 / 0

{
  "event_id": "LE06AS03_Reassembly_A_001_ego__right__0346",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "procedural"
  ],
  "qa_index": 0,
  "question": "Where did I place the screwdriver with the green and black handle using my right hand?",
  "answer": "I placed the screwdriver on the instruction sheet.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F9:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## LE06AS03_Reassembly_A_001_ego__right__0346 / 1

{
  "event_id": "LE06AS03_Reassembly_A_001_ego__right__0346",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "procedural"
  ],
  "qa_index": 1,
  "question": "What did I do with the black component immediately after placing the screwdriver down?",
  "answer": "I manipulated the black component with both hands.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F9:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## LE06AS03_Reassembly_A_002_ego__right__0208 / 0

{
  "event_id": "LE06AS03_Reassembly_A_002_ego__right__0208",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the tip of the torx screwdriver while holding it in my right hand?",
  "answer": "I positioned the tip of the screwdriver over a printed instruction sheet.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported tool identity: The visual evidence shows a screwdriver with a green/black handle, but the tip type (Torx) is not clearly visible or confirmed in the frames. The answer relies entirely on the annotation label 'torx_screwdriver' rather than visual evidence.",
      "Unsupported placement claim: While the screwdriver is held over the paper, the specific claim that the 'tip' was positioned over the 'instruction sheet' implies a level of precision and intent (e.g., pointing at a specific step) that is ambiguous in the low-resolution frames. The hand is generally over the paper, but the exact tip placement relative to the text/images is not definitively clear."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE06AS03_Reassembly_A_002_ego__right__0208 / 1

{
  "event_id": "LE06AS03_Reassembly_A_002_ego__right__0208",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "procedural"
  ],
  "qa_index": 1,
  "question": "What action did I take with the screwdriver after holding it over the instruction sheet?",
  "answer": "I placed the screwdriver down on the table.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## LE06AS03_Reassembly_A_004_ego__right__0080 / 0

{
  "event_id": "LE06AS03_Reassembly_A_004_ego__right__0080",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_part"
  ],
  "qa_index": 0,
  "question": "What did I do with the bevel gear after picking it up?",
  "answer": "I inserted the bevel gear into the motor housing and adjusted its position.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## LE06AS03_Reassembly_A_004_ego__right__0080 / 1

{
  "event_id": "LE06AS03_Reassembly_A_004_ego__right__0080",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_part"
  ],
  "qa_index": 1,
  "question": "How is the action of placing the bevel gear characterized in the annotation?",
  "answer": "The action is annotated as an anomaly with types 'spatial' and 'wrong_part'.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for annotation metadata rather than visual evidence; weak for anomaly understanding dataset."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE06AS03_Reassembly_B_005_ego__right__0174 / 0

{
  "event_id": "LE06AS03_Reassembly_B_005_ego__right__0174",
  "phase": "anomaly",
  "types": [
    "wrong_part",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the small, dark, cylindrical component after picking it up with my right hand?",
  "answer": "I inserted it into the central cavity of the housing held by my left hand and manipulated its position.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## LE06AS03_Reassembly_B_005_ego__right__0174 / 1

{
  "event_id": "LE06AS03_Reassembly_B_005_ego__right__0174",
  "phase": "anomaly",
  "types": [
    "wrong_part",
    "procedural"
  ],
  "qa_index": 1,
  "question": "Did I successfully complete the insertion of the bevel gear without any procedural issues?",
  "answer": "No, the action was annotated as an anomaly involving a wrong part and procedural error.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported causal claim: The answer asserts a 'wrong part' and 'procedural error' based solely on annotation metadata (F8), not visual evidence. The frames show insertion and manipulation, but do not visually confirm the part is incorrect or that the procedure failed.",
      "Label mistaken for visual evidence: The question asks about the success of the action, but the answer relies entirely on the 'anomaly' label rather than observable failure indicators (e.g., part falling out, visible misalignment).",
      "Generic annotation label: The question essentially asks the model to read the 'anomaly' tag, which is weak for an open-ended anomaly-understanding dataset."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE07UF17_Reassembly_A_002_ego__left__0018 / 0

{
  "event_id": "LE07UF17_Reassembly_A_002_ego__left__0018",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_part",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What object did my left hand hold during the interval from 115.38s to 129.11s?",
  "answer": "My left hand held a black gearbox housing with an attached silver drive shaft.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F10:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## LE07UF17_Reassembly_A_002_ego__left__0018 / 1

{
  "event_id": "LE07UF17_Reassembly_A_002_ego__left__0018",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_part",
    "procedural"
  ],
  "qa_index": 1,
  "question": "What actions did my right hand perform while my left hand held the gearbox housing?",
  "answer": "My right hand retrieved a small metallic component from Box 4, inserted it into the open face of the housing, and manipulated internal gears or mechanisms.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported tool identity: The answer claims the component was retrieved from 'Box 4', but the visual evidence in frame overview_f010 shows the hand reaching into the third orange bin (labeled 'Box 3'). The fourth bin is empty.",
      "Unsupported causal claim: The answer claims the right hand 'manipulated internal gears'. While the hand enters the housing, the specific action of manipulating gears is obscured by the housing rim and cannot be visually confirmed."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "fact:F10:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_A_001_ego__left__0110 / 0

{
  "event_id": "MA07LF04_Disassembly_A_001_ego__left__0110",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What action was my left hand performing on the M4 nut during the target interval?",
  "answer": "My left hand was attempting to loosen the M4 nut, as indicated by the 'hand_loosen_M4_nut' annotation, although visual evidence shows the hand maintained a static grip on the silver component.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": true,
    "duplicate": false,
    "issues": [
      "Unsupported causal claim: The answer asserts the hand was 'attempting to loosen' based solely on the annotation label, while visual evidence (F4) explicitly shows a static grip with no rotation.",
      "Answer leakage: The question asks 'What action...', and the answer immediately reveals the annotation label 'hand_loosen_M4_nut' which is the ground truth, rather than deriving the answer from visual observation.",
      "Label mistaken for evidence: The response conflates the semantic label with physical reality, failing to acknowledge the 'unknown' status of the actual motion."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_A_001_ego__left__0110 / 1

{
  "event_id": "MA07LF04_Disassembly_A_001_ego__left__0110",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "What phase was the target action of loosening the M4 nut classified as?",
  "answer": "The action was classified as a 'recovery' phase, suggesting an attempt to correct a previous issue, though the specific cause of the error is not visible.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": true,
    "duplicate": false,
    "issues": [
      "Unsupported causal claim: The answer speculates that the 'recovery' phase suggests an attempt to correct a previous issue, but the provided facts (F2) only state the classification, not the cause.",
      "Answer leakage: The question asks for the phase classification, and the answer directly quotes the annotation field 'recovery' without visual justification.",
      "Generic label question: The question asks for a metadata label rather than an understanding of the visual anomaly or procedure."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_A_003_ego__right__0088 / 0

{
  "event_id": "MA07LF04_Disassembly_A_003_ego__right__0088",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What action did my right hand perform on the screw during the target interval?",
  "answer": "The right hand picked up the screw from the work surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## MA07LF04_Disassembly_A_003_ego__right__0088 / 1

{
  "event_id": "MA07LF04_Disassembly_A_003_ego__right__0088",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "How is the phase of my right hand picking up the screw classified in the annotation?",
  "answer": "The action is classified as a recovery phase.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for an annotation label ('recovery phase') rather than a visual observation. While the answer is factually correct based on the metadata, it is not visually answerable from the video frames alone, which is a weak design for an anomaly-understanding dataset."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_B_005_ego__left__0044 / 0

{
  "event_id": "MA07LF04_Disassembly_B_005_ego__left__0044",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "handling"
  ],
  "qa_index": 0,
  "question": "What action did my left hand perform on the drive shaft during the target interval?",
  "answer": "The left hand rotated the gear end of the silver cylindrical motor component.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## MA07LF04_Disassembly_B_005_ego__left__0044 / 1

{
  "event_id": "MA07LF04_Disassembly_B_005_ego__left__0044",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "handling"
  ],
  "qa_index": 1,
  "question": "How is the execution of the drive shaft spinning by my left hand characterized in the annotation?",
  "answer": "The action is annotated as an anomaly involving temporal, spatial, and handling issues.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for annotation metadata (anomaly types) rather than visual evidence. While the answer is factually correct based on the provided JSON, it is not visually answerable from the frames alone."
    ],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## MA07LF04_Reassembly_A_001_ego__left__0134 / 0

{
  "event_id": "MA07LF04_Reassembly_A_001_ego__left__0134",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What action did my left hand perform on the angle grinder during the target interval?",
  "answer": "The left hand performed the action of attaching the lever.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported tool identity: The visual evidence shows the left hand manipulating the side handle (a fixed component), not a 'lever' (typically the trigger or lock-off). The annotation 'attach_lever' is not visually supported.",
      "Unsupported causal claim: The answer claims the phase is 'recovery' based on annotation metadata, but the visual frames do not show a preceding anomaly or a successful recovery action.",
      "Answer leakage: The question asks 'What action...', and the answer relies entirely on the provided annotation label rather than visual observation."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "fact:F9:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Reassembly_A_001_ego__left__0134 / 1

{
  "event_id": "MA07LF04_Reassembly_A_001_ego__left__0134",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "How is the phase of my left hand's lever attachment classified in relation to the preceding actions?",
  "answer": "The phase is classified as recovery, following neighbor actions labeled as anomalies.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported causal claim: The answer asserts the phase is 'recovery' following 'anomalies'. The provided frames show continuous manipulation without visual evidence of a prior error or a corrective recovery sequence.",
      "Label mistaken for evidence: The answer relies on the 'phase' metadata field rather than visual confirmation of the recovery process.",
      "Unsupported tool identity: The action is described as 'lever attachment', but the visual shows the side handle being adjusted."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "fact:F9:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Reassembly_B_005_ego__left__0101 / 0

{
  "event_id": "MA07LF04_Reassembly_B_005_ego__left__0101",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "handling",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did my left hand do with the black adapter plate during the target interval?",
  "answer": "The left hand removed the black adapter plate from the silver motor housing and placed it on the table.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported tool identity: The object removed is a black rubber gasket/seal, not an 'adapter plate' as claimed in the answer and facts.",
      "Unsupported hand scope: The visual evidence shows the left hand holding the motor housing while the right hand removes the black component. The answer incorrectly attributes the removal action to the left hand.",
      "Unsupported causal claim: The answer claims the left hand placed the object on the table, but the video shows the right hand performing the removal and placement."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "fact:F9:visual_without_observation",
    "fact:F10:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Reassembly_B_005_ego__left__0101 / 1

{
  "event_id": "MA07LF04_Reassembly_B_005_ego__left__0101",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "handling",
    "procedural"
  ],
  "qa_index": 1,
  "question": "How was the execution of the adapter plate dismount by my left hand categorized?",
  "answer": "The action was categorized as an anomaly involving temporal, spatial, handling, and procedural issues.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported tool identity: The question and answer refer to an 'adapter plate', but the visual evidence shows a rubber gasket/seal being manipulated.",
      "Unsupported hand scope: The question asks about the left hand's execution, but the primary action of removal is performed by the right hand.",
      "Label mistaken for visual evidence: The answer relies entirely on the annotation labels ('anomaly', 'temporal', etc.) rather than describing the visual anomaly (e.g., incorrect tool usage or part identification)."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "fact:F9:visual_without_observation",
    "fact:F10:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## NA07GE21_Disassembly_A_002_ego__left__0038 / 0

{
  "event_id": "NA07GE21_Disassembly_A_002_ego__left__0038",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my left hand do to the drive shaft during the target interval?",
  "answer": "I pulled the drive shaft away from the housing to separate the two components.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## NA07GE21_Disassembly_A_002_ego__left__0038 / 1

{
  "event_id": "NA07GE21_Disassembly_A_002_ego__left__0038",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did I successfully separate the drive shaft from the housing by the end of the action?",
  "answer": "Yes, the shaft and housing were fully separated by the end of the sequence.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## NA07GE21_Reassembly_A_001_ego__left__0049 / 0

{
  "event_id": "NA07GE21_Reassembly_A_001_ego__left__0049",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What action did my left hand perform during the recovery phase of the adapter plate attachment?",
  "answer": "My left hand picked up an M4 nut from the work surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## NA07GE21_Reassembly_A_001_ego__left__0049 / 1

{
  "event_id": "NA07GE21_Reassembly_A_001_ego__left__0049",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "Did my left hand successfully thread the M4 nut onto the component during this interval?",
  "answer": "It is not visible if the nut was successfully threaded, as the action concludes with the hands still in motion and the orientation obscured.",
  "answerability": "insufficient",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## SS07EL13_Disassembly_A_002_ego__right__0051 / 0

{
  "event_id": "SS07EL13_Disassembly_A_002_ego__right__0051",
  "phase": "anomaly",
  "types": [
    "temporal",
    "handling",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What tool did I use with my right hand to attempt loosening the screw?",
  "answer": "I used an orange-handled screwdriver.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F10:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## SS07EL13_Disassembly_A_002_ego__right__0051 / 1

{
  "event_id": "SS07EL13_Disassembly_A_002_ego__right__0051",
  "phase": "anomaly",
  "types": [
    "temporal",
    "handling",
    "wrong_tool"
  ],
  "qa_index": 1,
  "question": "What specific motion did my right hand perform with the screwdriver handle?",
  "answer": "I rotated the handle counter-clockwise while maintaining contact with the screw.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [
    "fact:F10:visual_without_observation"
  ],
  "strict_machine_pass": false
}

## SS07EL13_Reassembly_A_001_ego__right__0132 / 0

{
  "event_id": "SS07EL13_Reassembly_A_001_ego__right__0132",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What action was my right hand performing on the screw during the target interval?",
  "answer": "The right hand was loosening the screw.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported tool identity: The question asks about a 'screw', but the visual evidence shows the right hand manipulating a metallic ring or nut on the component shaft, not a screw. The screwdriver is lying unused on the table.",
      "Unsupported action: The action 'loosening' cannot be visually confirmed from the static frames; the hand is merely holding or rotating the component.",
      "Label mistaken for evidence: The answer relies entirely on the annotation label 'hand_loosen_screw' rather than visual confirmation of the specific object or motion."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## SS07EL13_Reassembly_A_001_ego__right__0132 / 1

{
  "event_id": "SS07EL13_Reassembly_A_001_ego__right__0132",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "What phase was the right hand's screw loosening action classified as?",
  "answer": "The action was classified as a recovery phase.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Unsupported causal claim: The question asks for the 'phase' classification, which is a metadata label ('recovery') and not a visual property of the video frames.",
      "Generic annotation label: The question only asks for a label defined in the annotation schema, failing to test anomaly understanding or visual reasoning.",
      "Uncertainty: The visual frames do not provide evidence to distinguish between 'normal', 'anomaly', or 'recovery' phases without external context."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## TO08CO25_Disassembly_B_005_ego__left__0009 / 0

{
  "event_id": "TO08CO25_Disassembly_B_005_ego__left__0009",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What tool did my left hand pick up from the table during the target interval?",
  "answer": "My left hand picked up an orange and yellow screwdriver.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}

## TO08CO25_Disassembly_B_005_ego__left__0009 / 1

{
  "event_id": "TO08CO25_Disassembly_B_005_ego__left__0009",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_tool"
  ],
  "qa_index": 1,
  "question": "Did my left hand select the green-handled or black-handled screwdriver that remained on the table?",
  "answer": "No, my left hand selected the orange and yellow screwdriver, while the green and black handled ones remained on the table.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
}
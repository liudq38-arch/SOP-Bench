# development v3 自动审核



{"ok": 20, "structural_issue_events": 10, "refined_events": 0, "conflict_events": 4, "strict_machine_pass": 13}



{"pass": 27, "reject": 8, "revise": 3}



Same-model independent-call audit; not human accuracy, not independent-model verification.



## ER10WE06_Reassembly_A_004_ego__right__0059 / 0

{
  "event_id": "ER10WE06_Reassembly_A_004_ego__right__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did my right hand use while contacting the black component?",
  "answer": "My right hand used an orange-handled screwdriver to maintain contact with the black component on the work surface.",
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
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## ER10WE06_Reassembly_A_004_ego__right__0059 / 1

{
  "event_id": "ER10WE06_Reassembly_A_004_ego__right__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did my right hand rotate the screwdriver while pressing it against the component?",
  "answer": "No visible rotation or displacement of the screwdriver was observed while the right hand maintained contact with the component.",
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
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_002_ego__right__0070 / 0

{
  "event_id": "KI03AR28_Disassembly_A_002_ego__right__0070",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do with the green-handled screwdriver during the target interval?",
  "answer": "The right hand held the green-handled screwdriver vertically, keeping its tip in contact with the top of the black component while the left hand stabilized it.",
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
    "0:context_evidence_for_target_claim",
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_002_ego__right__0070 / 1

{
  "event_id": "KI03AR28_Disassembly_A_002_ego__right__0070",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did I encounter any anomalies while aligning the screw with the right hand?",
  "answer": "No anomalies were recorded for this action; the phase is labeled as normal, and the screwdriver tip remained in stable contact with the component.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer relies on annotation label 'normal' rather than visual evidence.",
      "Static frames cannot confirm absence of anomalies or successful alignment."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "0:context_evidence_for_target_claim",
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_004_ego__right__0090 / 0

{
  "event_id": "KI03AR28_Disassembly_A_004_ego__right__0090",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do with the orange-handled screwdriver during the target interval?",
  "answer": "My right hand lifted the orange-handled screwdriver from the workbench surface and moved it toward the black motor assembly held by the left hand.",
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
    "observation:O1:invalid_evidence",
    "observation:O2:invalid_evidence",
    "observation:O3:invalid_evidence",
    "observation:O4:invalid_evidence",
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_004_ego__right__0090 / 1

{
  "event_id": "KI03AR28_Disassembly_A_004_ego__right__0090",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Where did I position the screwdriver tip after lifting it?",
  "answer": "I positioned the screwdriver tip against the side of the black motor assembly held by my left hand.",
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
    "observation:O1:invalid_evidence",
    "observation:O2:invalid_evidence",
    "observation:O3:invalid_evidence",
    "observation:O4:invalid_evidence",
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## KI05KO01_Disassembly_A_002_ego__right__0084 / 0

{
  "event_id": "KI05KO01_Disassembly_A_002_ego__right__0084",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do to the screw on the black component?",
  "answer": "My right hand held a screwdriver against the screw, rotated it to loosen the screw, and then removed the loosened screw from the component.",
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
  "question": "What tool did my right hand use to interact with the screw?",
  "answer": "My right hand used a screwdriver to hold against, rotate, and remove the screw from the black component.",
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
  "question": "What did my right hand pick up from the surface during the target interval?",
  "answer": "The right hand picked up a small silver metal part from the surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object identity 'screw' is not visually verifiable; appears to be a pin or generic metal part.",
      "Question asks for specific object identity not supported by visual evidence."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
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
  "question": "What did my right hand do with the black component before picking up the silver part?",
  "answer": "The right hand placed the black component onto the white surface before picking up the silver part.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for sequence of events visible in the frames.",
      "Action of placing black component precedes picking up silver part."
    ],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
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
  "question": "What did I do with the screwdriver over the instruction sheet?",
  "answer": "I held the screwdriver over the sheet, moved it across the images, and then placed it down on the paper.",
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
    "observation:O1:invalid_evidence",
    "observation:O2:invalid_evidence",
    "observation:O3:invalid_evidence",
    "observation:O4:invalid_evidence",
    "observation:O5:invalid_evidence",
    "0:invalid_visual_refs",
    "1:invalid_visual_refs"
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
  "question": "How did my action sequence differ from the prior step on the black component?",
  "answer": "Previously, I used the screwdriver on the black component; during the target interval, I moved it to the instruction sheet and placed it there.",
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
    "observation:O1:invalid_evidence",
    "observation:O2:invalid_evidence",
    "observation:O3:invalid_evidence",
    "observation:O4:invalid_evidence",
    "observation:O5:invalid_evidence",
    "0:invalid_visual_refs",
    "1:invalid_visual_refs"
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
  "question": "What did my right hand do with the screwdriver during the target interval?",
  "answer": "The right hand held a green and black screwdriver, pointing it at an instruction sheet and tracing a diagram without touching the mechanical parts.",
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
  "question": "Did my right hand contact the mechanical assembly while holding the screwdriver?",
  "answer": "No, the right hand did not make physical contact with the mechanical parts during the target interval, only interacting with the instruction sheet.",
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
  "question": "What did my right hand do with the small black component during the target interval?",
  "answer": "The right hand moved the small black component toward the angle grinder body and placed it into the central opening before withdrawing.",
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
  "question": "How does the sequence of actions relate to the placement of the bevel gear?",
  "answer": "The placement of the bevel gear occurred after picking it up and before picking up the drive shaft, as indicated by the action sequence.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer relies on annotation metadata, not visual evidence.",
      "Question asks for sequence info not visible in frames."
    ],
    "decision": "reject"
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
  "question": "What did my right hand insert into the silver housing during the target interval?",
  "answer": "The right hand inserted a small metal ring into the central opening of the silver housing held by the left hand.",
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
  "question": "How did my right hand manipulate the ring after inserting it into the housing?",
  "answer": "The right hand pressed and rotated the ring within the housing cavity to adjust its position before withdrawing.",
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
  "question": "What did my left hand do to the motor housing during the target interval?",
  "answer": "The left hand held the black motor housing steady while the right hand manipulated the front assembly.",
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
  "question": "What did my right hand do to the small metal part inserted into the assembly?",
  "answer": "The right hand rotated the inserted metal part within the assembly while the left hand maintained its grip.",
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

## MA07LF04_Disassembly_A_001_ego__left__0110 / 0

{
  "event_id": "MA07LF04_Disassembly_A_001_ego__left__0110",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did my left hand do to the assembly during the target interval?",
  "answer": "The left hand held the black housing steady on the workbench, maintaining a static grip to stabilize the assembly while the right hand operated a tool.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for target action 'loosen', but answer describes static 'holding' which contradicts the target label.",
      "Static frames cannot verify the dynamic 'loosening' action or the 'recovery' phase claimed in annotations."
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
  "question": "Where did I place the black circular component with my right hand?",
  "answer": "I placed the black circular component into the third orange bin labeled 'Box 3'.",
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
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_A_003_ego__right__0088 / 1

{
  "event_id": "MA07LF04_Disassembly_A_003_ego__right__0088",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "What phase is annotated for the action where I handled the black component?",
  "answer": "The annotation labels this action phase as 'recovery', though no specific anomaly types are listed.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for annotation label, not visual evidence.",
      "Answer relies solely on metadata, not frame content."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "1:context_evidence_for_target_claim"
  ],
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
  "question": "What did my left hand do to the motor component during the target interval?",
  "answer": "The left hand held the cylindrical motor component steady while the right hand pulled the gear housing away, then rotated it to display the internal shaft.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer claims right hand pulled gear housing away, but frames show left hand separating parts.",
      "Target action 'spin' is not visually supported; frames show separation and static holding."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
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
  "question": "How did the left hand position the motor component after separating it from the gear housing?",
  "answer": "After separation, the left hand rotated the component to show the internal shaft and stator area, then held it upright displaying the open end.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer claims rotation to show internal shaft, but frames show static holding of the component.",
      "Question asks for placement after separation, but separation action is not fully visible in target frames."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Reassembly_A_001_ego__left__0134 / 0

{
  "event_id": "MA07LF04_Reassembly_A_001_ego__left__0134",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did my left hand do to the angle grinder housing during the target interval?",
  "answer": "The left hand held the black housing steady on the workbench, maintaining a static grip without visible movement throughout the interval.",
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

## MA07LF04_Reassembly_A_001_ego__left__0134 / 1

{
  "event_id": "MA07LF04_Reassembly_A_001_ego__left__0134",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "Did my left hand use the wrench or screwdriver visible on the table?",
  "answer": "No, the left hand did not touch the wrench or screwdriver lying on the table; it only supported the grinder housing.",
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
  "question": "What did my left hand do to the motor shaft during the target interval?",
  "answer": "The left hand held the cylindrical motor shaft while the right hand rotated the silver housing, maintaining grip as the assembly tilted.",
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
    "observation:O1:invalid_evidence",
    "observation:O2:invalid_evidence",
    "observation:O3:invalid_evidence",
    "observation:O4:invalid_evidence",
    "observation:O5:invalid_evidence"
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
  "question": "How did my left hand behave towards the end of the target interval?",
  "answer": "Towards the end of the interval, the left hand released the motor shaft and rested on the workbench surface.",
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
    "observation:O1:invalid_evidence",
    "observation:O2:invalid_evidence",
    "observation:O3:invalid_evidence",
    "observation:O4:invalid_evidence",
    "observation:O5:invalid_evidence"
  ],
  "strict_machine_pass": false
}

## NA07GE21_Disassembly_A_002_ego__left__0038 / 0

{
  "event_id": "NA07GE21_Disassembly_A_002_ego__left__0038",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my left hand do to the silver motor shaft assembly during the target interval?",
  "answer": "The left hand held the silver motor shaft assembly steady and maintained a static grip while the right hand pulled the housing away.",
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
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## NA07GE21_Disassembly_A_002_ego__left__0038 / 1

{
  "event_id": "NA07GE21_Disassembly_A_002_ego__left__0038",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "Did my left hand perform the extraction action without any visible anomalies?",
  "answer": "Yes, the left hand performed the extraction action in a normal phase with no anomaly types listed in the annotation.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer relies on annotation metadata, not visual evidence.",
      "Question asks for visual confirmation of a label."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## NA07GE21_Reassembly_A_001_ego__left__0049 / 0

{
  "event_id": "NA07GE21_Reassembly_A_001_ego__left__0049",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did my left hand do to the black component held by my right hand?",
  "answer": "My left hand moved from the table and grasped the cylindrical side of the black component held by the right hand.",
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
    "0:context_evidence_for_target_claim",
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}

## NA07GE21_Reassembly_A_001_ego__left__0049 / 1

{
  "event_id": "NA07GE21_Reassembly_A_001_ego__left__0049",
  "phase": "recovery",
  "types": [],
  "qa_index": 1,
  "question": "Did my left hand successfully pick up an M4 nut during this interval?",
  "answer": "The annotation labels the action as picking up an M4 nut, but visual evidence only confirms grasping a black component, leaving the object identity uncertain.",
  "answerability": "annotation_only",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Visual evidence shows grasping a large component, not picking up a nut.",
      "Object identity relies solely on annotation, not visual verification."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "0:context_evidence_for_target_claim",
    "1:context_evidence_for_target_claim"
  ],
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
  "question": "What did my right hand do with the small metal part inside the black component?",
  "answer": "The right hand inserted the small metal part into the central opening, rotated it, adjusted it with fingers, and then removed it to hold separately.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer claims 'removed' part, but frames show insertion/rotation only.",
      "Question asks for action details already fully listed in the answer."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
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
  "question": "How did my right hand interact with the black cylindrical component during the sequence?",
  "answer": "The right hand held the black cylindrical component while the left hand supported it, then manipulated a small metal part within its central opening.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer claims 'manipulated' part, but frames show insertion/rotation only.",
      "Question asks for interaction details already fully listed in the answer."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## SS07EL13_Reassembly_A_001_ego__right__0132 / 0

{
  "event_id": "SS07EL13_Reassembly_A_001_ego__right__0132",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do with the black component during the target interval?",
  "answer": "My right hand maintained a static grip on the black cylindrical component with a silver shaft throughout the interval, without performing a visible loosening motion.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": true,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks for action, answer correctly identifies static grip based on visual evidence."
    ],
    "decision": "pass"
  },
  "structural_issues": [],
  "strict_machine_pass": true
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
  "question": "What tool did my left hand pick up from the workbench?",
  "answer": "My left hand grasped and lifted an orange-handled screwdriver from the workbench surface.",
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
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
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
  "question": "Where did my left hand move the screwdriver after lifting it?",
  "answer": "After lifting the screwdriver, my left hand moved it towards the metal assembly held by the right hand.",
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
    "1:context_evidence_for_target_claim"
  ],
  "strict_machine_pass": false
}
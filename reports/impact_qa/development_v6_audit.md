# development v6 自动审核



{"ok": 20, "structural_issue_events": 5, "refined_events": 0, "conflict_events": 9, "strict_machine_pass": 12}



{"pass": 17, "revise": 2, "reject": 3}



Same-model independent-call audit; not human accuracy, not independent-model verification.



## ER10WE06_Reassembly_A_004_ego__right__0059 / 0

{
  "event_id": "ER10WE06_Reassembly_A_004_ego__right__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the orange-handled screwdriver against the black component?",
  "answer": "I held the screwdriver against the component, maintaining a steady grip and applying pressure while the tip remained engaged.",
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

## KI03AR28_Disassembly_A_002_ego__right__0070 / 0

{
  "event_id": "KI03AR28_Disassembly_A_002_ego__right__0070",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the screwdriver tip on the motor housing?",
  "answer": "I kept the screwdriver tip engaged with the central screw of the motor housing.",
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

## KI03AR28_Disassembly_A_004_ego__right__0090 / 0

{
  "event_id": "KI03AR28_Disassembly_A_004_ego__right__0090",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did I grasp and lift with my right hand?",
  "answer": "I grasped and lifted an orange-handled screwdriver.",
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

## KI05KO01_Disassembly_A_002_ego__right__0084 / 0

{
  "event_id": "KI05KO01_Disassembly_A_002_ego__right__0084",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the fastener near the shaft?",
  "answer": "I moved the fastener to contact the shaft end and rotated it against the shaft.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Visual evidence shows the right hand holding a fastener, not moving it to contact the shaft.",
      "Rotation of the fastener against the shaft is not visible in the provided frames."
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
  "question": "What did I pick up with my right hand?",
  "answer": "I picked up a small metal fastener from the gray mat.",
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
    "1:duplicate_dimension"
  ],
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
  "question": "How did I move the fastener with my right hand?",
  "answer": "I moved the fastener toward the tool body while maintaining a steady grip.",
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
    "1:duplicate_dimension"
  ],
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
  "question": "What did I do with the screwdriver while looking at the instruction sheet?",
  "answer": "I pointed the screwdriver tip at the 'Schritt 3' image, then moved it to point at 'Schritt 5'.",
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
  "question": "What did I do with the torx screwdriver in my right hand?",
  "answer": "I held the torx screwdriver and pointed its tip at an instruction sheet diagram.",
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

## LE06AS03_Reassembly_A_004_ego__right__0080 / 0

{
  "event_id": "LE06AS03_Reassembly_A_004_ego__right__0080",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_part"
  ],
  "qa_index": 0,
  "question": "What did I do with the small black fastener near the motor assembly?",
  "answer": "I moved it closer to the motor's central shaft and aligned it for insertion.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object mismatch: video shows a white cylindrical part, not a black fastener.",
      "Action unsupported: no visible movement or alignment of the part is shown."
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
  "question": "What did I do with the small metal fastener after picking it up?",
  "answer": "I inserted the fastener into the central hole of the angle grinder head.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object misidentified: visual shows a gear, not a fastener.",
      "Unsupported claim of 'tightening' or 'securing' the object."
    ],
    "decision": "revise"
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
  "question": "What did I do with the angle grinder body using my left hand?",
  "answer": "I held the angle grinder body steady throughout the observed interval.",
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
    "0:unsupported_continuous_motion_claim"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_A_001_ego__left__0110 / 0

{
  "event_id": "MA07LF04_Disassembly_A_001_ego__left__0110",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did my left hand do to the angle grinder shaft?",
  "answer": "It maintained a static grip on the silver cylindrical shaft throughout the interval.",
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
    "0:unsupported_continuous_motion_claim"
  ],
  "strict_machine_pass": false
}

## MA07LF04_Disassembly_A_003_ego__right__0088 / 0

{
  "event_id": "MA07LF04_Disassembly_A_003_ego__right__0088",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the small black circular component after lifting it?",
  "answer": "I rotated the component to expose its underside before placing it back on the table.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks about a component, but target action is picking up a screw.",
      "Visual evidence shows lifting a component, not the annotated screw pickup."
    ],
    "decision": "reject"
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
  "question": "What did I do with the motor armature using my left hand?",
  "answer": "I held the commutator end and rotated the armature slightly to demonstrate shaft movement.",
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

## MA07LF04_Reassembly_A_001_ego__left__0134 / 0

{
  "event_id": "MA07LF04_Reassembly_A_001_ego__left__0134",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "How did I hold the black motor housing with my left hand?",
  "answer": "I held it steady with my fingers on the upper rim, maintaining a static grip.",
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
    "0:unsupported_continuous_motion_claim"
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
  "question": "What did I do with the black circular component after removing it from the motor shaft?",
  "answer": "I placed the removed black component onto the white surface.",
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

## NA07GE21_Disassembly_A_002_ego__left__0038 / 0

{
  "event_id": "NA07GE21_Disassembly_A_002_ego__left__0038",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the motor shaft assembly held in my left hand?",
  "answer": "I pulled the shaft assembly away from the black housing, separating the two components.",
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

## NA07GE21_Reassembly_A_001_ego__left__0049 / 0

{
  "event_id": "NA07GE21_Reassembly_A_001_ego__left__0049",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I pick up with my left hand?",
  "answer": "I picked up a small fastener from the instruction sheet.",
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
  "question": "Where did I insert the fastener with my left hand?",
  "answer": "I inserted the fastener into the side of the motor assembly.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Insertion action not visible in target interval; only pickup shown.",
      "Answer claims outcome not supported by visual evidence."
    ],
    "decision": "reject"
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
  "question": "What did I do with the motor housing while the left hand manipulated the shaft?",
  "answer": "I held the motor housing steady.",
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

## SS07EL13_Reassembly_A_001_ego__right__0132 / 0

{
  "event_id": "SS07EL13_Reassembly_A_001_ego__right__0132",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do to the angle grinder body during the interval?",
  "answer": "It maintained a static grip on the body without moving any parts or manipulating the screw.",
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
    "0:unsupported_continuous_motion_claim"
  ],
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
  "question": "What tool did I grasp with my left hand from the instruction sheet?",
  "answer": "I grasped the orange-handled screwdriver from the table.",
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
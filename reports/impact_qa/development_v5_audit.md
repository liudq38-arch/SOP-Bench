# development v5 自动审核



{"ok": 20, "structural_issue_events": 3, "refined_events": 0, "conflict_events": 4, "strict_machine_pass": 16}



{"pass": 18, "reject": 3, "revise": 1}



Same-model independent-call audit; not human accuracy, not independent-model verification.



## ER10WE06_Reassembly_A_004_ego__right__0059 / 0

{
  "event_id": "ER10WE06_Reassembly_A_004_ego__right__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did I hold against the small black component with my right hand?",
  "answer": "I held an orange-handled screwdriver with its tip positioned against the component.",
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
  "question": "What did I do with the green-handled screwdriver in my right hand?",
  "answer": "I held it vertically above a black motor component with a static grip.",
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

## KI03AR28_Disassembly_A_004_ego__right__0090 / 0

{
  "event_id": "KI03AR28_Disassembly_A_004_ego__right__0090",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What tool did I grasp and lift with my right hand?",
  "answer": "I grasped and lifted an orange-handled screwdriver from the work surface.",
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
  "question": "What did I do with the small metal part after inserting it into the shaft?",
  "answer": "I rotated the inserted metal part clockwise while the left hand stabilized the component.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Visual evidence shows insertion, not extraction of the bearing plate.",
      "Answer claims clockwise rotation, but visual sequence shows counter-clockwise motion."
    ],
    "decision": "reject"
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
  "answer": "I picked up a small metal part from the gray mat.",
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
  "question": "Where did I place the small metal part?",
  "answer": "I placed the small metal part back onto the gray mat.",
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
  "question": "What did I do with the screwdriver tip while holding it with my right hand?",
  "answer": "I moved the screwdriver downward and made the tip contact the black component.",
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
  "question": "What object did I hold with my right hand?",
  "answer": "I held a green-handled screwdriver vertically above the instruction sheet.",
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
  "question": "What did I do with the tool near the motor assembly?",
  "answer": "I held the tool with a white cylindrical attachment steady near the motor without visible rotation.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks about tool use, but target action is placing a bevel gear.",
      "Visual evidence shows gear placement, contradicting the tool-focused answer."
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
  "question": "What did I do with the small dark component after picking it up?",
  "answer": "I inserted it into the central cavity of the metal housing and then rotated it.",
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
  "question": "What did I do with the black motor-like component in my left hand?",
  "answer": "I held the component and rotated it slightly while the right hand adjusted internal parts.",
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

## MA07LF04_Disassembly_A_001_ego__left__0110 / 0

{
  "event_id": "MA07LF04_Disassembly_A_001_ego__left__0110",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the silver cylindrical component using my left hand?",
  "answer": "I held the silver cylindrical component steady against the black housing.",
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

## MA07LF04_Disassembly_A_003_ego__right__0088 / 0

{
  "event_id": "MA07LF04_Disassembly_A_003_ego__right__0088",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the small black component on the workbench?",
  "answer": "I lifted the small black component vertically off the table with my right hand.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object mismatch: visual evidence shows lifting a black component, not a screw.",
      "Action mismatch: target action hint specifies 'pick_up_screw', but frames show lifting a component."
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
  "question": "What object did my left hand hold during the interval?",
  "answer": "My left hand held a grey plastic gear component with a metal shaft protruding from its center.",
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
  "question": "What did I do with the black motor housing using my left hand?",
  "answer": "I held the black motor housing steady against the workbench surface.",
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
  "question": "What did I do with the black circular component near the motor assembly?",
  "answer": "I held it near the motor assembly and then released it onto the work surface.",
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
  "question": "How did I handle the silver motor housing?",
  "answer": "I grasped the housing while the right hand supported it, maintained the grip, and then released it.",
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

## NA07GE21_Disassembly_A_002_ego__left__0038 / 0

{
  "event_id": "NA07GE21_Disassembly_A_002_ego__left__0038",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the motor shaft assembly using my left hand?",
  "answer": "I maintained a static grip on the motor shaft assembly throughout the interval.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks 'What did I do' implying an action, but the answer describes a static state.",
      "Visual evidence shows the left hand holding the shaft while the right hand manipulates the housing, contradicting the 'static' claim for the whole assembly."
    ],
    "decision": "revise"
  },
  "structural_issues": [
    "0:unsupported_continuous_motion_claim"
  ],
  "strict_machine_pass": false
}

## NA07GE21_Reassembly_A_001_ego__left__0049 / 0

{
  "event_id": "NA07GE21_Reassembly_A_001_ego__left__0049",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the small metal part after picking it up?",
  "answer": "I moved it towards the black assembly held by the right hand.",
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
  "question": "What did I do with the small metal part after inserting it into the black component?",
  "answer": "I rotated the inserted metal part inside the component with my right hand.",
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
  "question": "What did I do with the small metal part on the assembly?",
  "answer": "I rotated and adjusted its position while maintaining continuous contact.",
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

## TO08CO25_Disassembly_B_005_ego__left__0009 / 0

{
  "event_id": "TO08CO25_Disassembly_B_005_ego__left__0009",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What object did I grasp and lift with my left hand?",
  "answer": "I grasped and lifted the handle of the orange and yellow screwdriver off the mat.",
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
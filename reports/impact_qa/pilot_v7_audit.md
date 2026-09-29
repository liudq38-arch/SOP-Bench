# pilot v7 自动审核



{"ok": 60, "structural_issue_events": 9, "refined_events": 1, "conflict_events": 15, "strict_machine_pass": 37}



{"pass": 43, "revise": 9, "reject": 12}



Same-model independent-call audit; not human accuracy, not independent-model verification.



## AL07EJ17_Disassembly_A_001_ego__right__0054 / 0

{
  "event_id": "AL07EJ17_Disassembly_A_001_ego__right__0054",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial"
  ],
  "qa_index": 0,
  "question": "Where did I place the screwdriver with my right hand?",
  "answer": "I placed the screwdriver onto the printed instruction sheet.",
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

## AL07EJ17_Disassembly_A_004_ego__left__0001 / 0

{
  "event_id": "AL07EJ17_Disassembly_A_004_ego__left__0001",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the black tool handle held in my left hand?",
  "answer": "I moved it toward the leftmost orange bin, lowered it inside, and withdrew, leaving it stored.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object identity unsupported: 'black tool handle' is not visually confirmed.",
      "Outcome unsupported: 'leaving it stored' cannot be verified from the frames."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## AL07EJ17_Disassembly_B_005_ego__right__0085 / 0

{
  "event_id": "AL07EJ17_Disassembly_B_005_ego__right__0085",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the orange-handled screwdriver on the table?",
  "answer": "I grasped the screwdriver, lifted it off the table, and positioned its tip against a metal component.",
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

## AL07EJ17_Reassembly_A_004_ego__right__0060 / 0

{
  "event_id": "AL07EJ17_Reassembly_A_004_ego__right__0060",
  "phase": "anomaly",
  "types": [
    "temporal",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What tool did I hold with my right hand?",
  "answer": "I held a screwdriver with a black and green handle.",
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

## AL07EJ17_Reassembly_A_004_ego__right__0060 / 1

{
  "event_id": "AL07EJ17_Reassembly_A_004_ego__right__0060",
  "phase": "anomaly",
  "types": [
    "temporal",
    "procedural"
  ],
  "qa_index": 1,
  "question": "Where did I position the screwdriver tip?",
  "answer": "I positioned the tip over a dark circular object held by the left hand.",
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

## ER07AD15_Disassembly_A_002_ego__right__0057 / 0

{
  "event_id": "ER07AD15_Disassembly_A_002_ego__right__0057",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "Where was my right hand positioned during the interval?",
  "answer": "It was positioned over the fourth orange bin adjacent to the blue bin.",
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

## ER07AD15_Reassembly_A_001_ego__left__0002 / 0

{
  "event_id": "ER07AD15_Reassembly_A_001_ego__left__0002",
  "phase": "anomaly",
  "types": [
    "handling",
    "wrong_part"
  ],
  "qa_index": 0,
  "question": "What did I do with the brass-colored drive shaft using my left hand?",
  "answer": "I gripped and rotated the brass-colored drive shaft while applying continuous rotational force.",
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

## ER07AD15_Reassembly_A_002_ego__right__0046 / 0

{
  "event_id": "ER07AD15_Reassembly_A_002_ego__right__0046",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the small black component using my right hand?",
  "answer": "I inserted it into the silver flange of the motor housing.",
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

## ER07AD15_Reassembly_A_002_ego__right__0046 / 1

{
  "event_id": "ER07AD15_Reassembly_A_002_ego__right__0046",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "How did I adjust the component after inserting it?",
  "answer": "I rotated the internal component slightly within the assembly.",
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

## ER10WE06_Disassembly_A_003_ego__left__0026 / 0

{
  "event_id": "ER10WE06_Disassembly_A_003_ego__left__0026",
  "phase": "anomaly",
  "types": [
    "handling"
  ],
  "qa_index": 0,
  "question": "What did I do with the tool inside the motor housing?",
  "answer": "I rotated the tool inside the housing to spin the internal fan.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Target hand is left, but video shows right hand manipulating the tool.",
      "No visible rotation of internal fan; motion is too subtle to confirm outcome."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## ER10WE06_Disassembly_A_004_ego__right__0043 / 0

{
  "event_id": "ER10WE06_Disassembly_A_004_ego__right__0043",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the orange-handled screwdriver after grasping it?",
  "answer": "I lifted the screwdriver off the table surface and moved it towards the angle grinder.",
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

## ER10WE06_Reassembly_A_001_ego__right__0073 / 0

{
  "event_id": "ER10WE06_Reassembly_A_001_ego__right__0073",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do to the black circular component with my right hand?",
  "answer": "I rotated it to expose the threaded stud and flipped it to reveal the flat side with internal teeth.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Video shows only slight rotation; flipping to reveal flat side is not visible.",
      "Internal teeth are not clearly visible in any provided frame."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## ER10WE06_Reassembly_A_002_ego__right__0096 / 0

{
  "event_id": "ER10WE06_Reassembly_A_002_ego__right__0096",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What motion did I perform with the screwdriver handle using my right hand?",
  "answer": "I rotated the green-handled screwdriver clockwise while applying torque to the black component.",
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

## ER10WE06_Reassembly_A_003_ego__right__0074 / 0

{
  "event_id": "ER10WE06_Reassembly_A_003_ego__right__0074",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "How did my right hand contact the angle grinder housing during the interval?",
  "answer": "My right hand held the housing steady, with fingertips contacting the edge to maintain alignment.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Right hand is inside the housing, not holding the edge.",
      "Fingertip contact with the edge is not visible."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## ER10WE06_Reassembly_B_005_ego__right__0081 / 0

{
  "event_id": "ER10WE06_Reassembly_B_005_ego__right__0081",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the small dark fastener?",
  "answer": "I lifted it from the mat and pressed it into the silver component's center.",
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

## KE03ER16_Disassembly_A_001_ego__right__0068 / 0

{
  "event_id": "KE03ER16_Disassembly_A_001_ego__right__0068",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial"
  ],
  "qa_index": 0,
  "question": "What did I do with the small metallic tool?",
  "answer": "I placed it on the gray circular mat and released it.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object identity unclear: the item handled is not visibly a 'small metallic tool'.",
      "Release action not visible: hand remains in contact with the object in all target frames."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KE03ER16_Disassembly_A_003_ego__right__0058 / 0

{
  "event_id": "KE03ER16_Disassembly_A_003_ego__right__0058",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the angle grinder component?",
  "answer": "I lowered it into the blue bin labeled 'Box 5' and released it.",
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

## KE03ER16_Reassembly_A_001_ego__left__0040 / 0

{
  "event_id": "KE03ER16_Reassembly_A_001_ego__left__0040",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the black motor housing while the right hand rotated the screwdriver?",
  "answer": "I held the black motor housing steady on the table to stabilize it during the fastening motion.",
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

## KE03ER16_Reassembly_A_002_ego__left__0039 / 0

{
  "event_id": "KE03ER16_Reassembly_A_002_ego__left__0039",
  "phase": "anomaly",
  "types": [
    "temporal",
    "handling"
  ],
  "qa_index": 0,
  "question": "What did I do with the angle grinder body using my left hand?",
  "answer": "I held the black angle grinder body steady on the mat without releasing it.",
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

## KE03ER16_Reassembly_A_003_ego__right__0056 / 0

{
  "event_id": "KE03ER16_Reassembly_A_003_ego__right__0056",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What object did I grasp with my right hand from the table?",
  "answer": "I grasped an orange-handled tool from the table surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Target interval shows tool already in hand; grasp action not visible.",
      "Question asks for grasp event not present in target frames."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI03AR28_Disassembly_A_001_ego__right__0097 / 0

{
  "event_id": "KI03AR28_Disassembly_A_001_ego__right__0097",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "Where did I place the small black component with my right hand?",
  "answer": "I placed it into the bin labeled 'Box 4'.",
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

## KI03AR28_Disassembly_B_005_ego__right__0098 / 0

{
  "event_id": "KI03AR28_Disassembly_B_005_ego__right__0098",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What did I do with the green-handled tool?",
  "answer": "I grasped the green-handled screwdriver and lifted it from the table.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer claims lifting the tool, but video shows the hand only reaching and hovering over it.",
      "Contact with the green-handled screwdriver is not visually confirmed in the provided frames."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI03AR28_Reassembly_A_001_ego__left__0045 / 0

{
  "event_id": "KI03AR28_Reassembly_A_001_ego__left__0045",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial"
  ],
  "qa_index": 0,
  "question": "What did my left hand do with the motor housing during the interval?",
  "answer": "It remained stationary on the table surface near the housing without grasping or moving it.",
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

## KI03AR28_Reassembly_A_003_ego__left__0007 / 0

{
  "event_id": "KI03AR28_Reassembly_A_003_ego__left__0007",
  "phase": "anomaly",
  "types": [
    "temporal",
    "handling"
  ],
  "qa_index": 0,
  "question": "What did I do with my left hand while the right hand rotated the component?",
  "answer": "I gripped the cylindrical motor shaft to stabilize the assembly.",
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

## KI03AR28_Reassembly_A_004_ego__right__0069 / 0

{
  "event_id": "KI03AR28_Reassembly_A_004_ego__right__0069",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "How did I manipulate the fastener while inserting it into the housing?",
  "answer": "I rotated the fastener with my fingertips while pushing it deeper into the central hole.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Rotation of the fastener is not visually evident in the provided frames.",
      "Insertion into the housing cannot be confirmed as the part remains in the hand."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI03AR28_Reassembly_B_005_ego__left__0021 / 0

{
  "event_id": "KI03AR28_Reassembly_B_005_ego__left__0021",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What object did I hold with my left hand?",
  "answer": "I held a carburetor body with my left hand.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": true,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object is a carburetor, not an angle grinder; task label mismatch.",
      "Answer claims 'angle grinder reassembly' which contradicts visible carburetor."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI03AR28_Reassembly_B_005_ego__left__0021 / 1

{
  "event_id": "KI03AR28_Reassembly_B_005_ego__left__0021",
  "phase": "normal",
  "types": [],
  "qa_index": 1,
  "question": "How did I use my left hand while the right hand worked?",
  "answer": "I stabilized the object on the work surface.",
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

## KI05KO01_Disassembly_A_001_ego__right__0156 / 0

{
  "event_id": "KI05KO01_Disassembly_A_001_ego__right__0156",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the orange-handled screwdriver on the table?",
  "answer": "I grasped the screwdriver, lifted it off the table, and moved it vertically away from the instruction sheet.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Answer claims lifting and moving away, but frames show the tool remaining on the table.",
      "Action described is not visible in the provided target interval frames."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI05KO01_Disassembly_A_003_ego__left__0028 / 0

{
  "event_id": "KI05KO01_Disassembly_A_003_ego__left__0028",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the black circular object after lifting it from the bin?",
  "answer": "I placed the black circular object back into the bin.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Video shows the object being placed into the bin, but the lifting action is not visible.",
      "Question assumes a prior action (lifting) that cannot be verified from the provided frames."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI05KO01_Disassembly_B_005_ego__left__0032 / 0

{
  "event_id": "KI05KO01_Disassembly_B_005_ego__left__0032",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the silver cylindrical component using my left hand?",
  "answer": "I lowered it into the blue bin labeled 'Box 5' and released it inside.",
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

## KI05KO01_Reassembly_A_001_ego__left__0011 / 0

{
  "event_id": "KI05KO01_Reassembly_A_001_ego__left__0011",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the drive shaft while the right hand manipulated the housing?",
  "answer": "I held the drive shaft steady to support the assembly during the housing adjustment.",
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

## KI05KO01_Reassembly_A_003_ego__right__0084 / 0

{
  "event_id": "KI05KO01_Reassembly_A_003_ego__right__0084",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "How did I tighten the black collar on the silver tool shaft?",
  "answer": "I rotated the collar clockwise with my fingertips while maintaining a firm grip.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Clockwise rotation direction is not visually verifiable from static crops.",
      "Specific 'fingertip' contact and 'firm grip' details are unsupported by visual evidence."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KI05KO01_Reassembly_B_005_ego__left__0019 / 0

{
  "event_id": "KI05KO01_Reassembly_B_005_ego__left__0019",
  "phase": "anomaly",
  "types": [
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the angle grinder handle using my left hand?",
  "answer": "I maintained a steady grip on the handle throughout the interval.",
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

## KI05KO01_Reassembly_B_005_ego__left__0019 / 1

{
  "event_id": "KI05KO01_Reassembly_B_005_ego__left__0019",
  "phase": "anomaly",
  "types": [
    "procedural"
  ],
  "qa_index": 1,
  "question": "Did any parts of the angle grinder detach during this sequence?",
  "answer": "No parts were detached or removed; the tool remained assembled.",
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
    "0:unsupported_continuous_motion_claim"
  ],
  "strict_machine_pass": true
}

## KJ03JM25_Disassembly_A_004_ego__left__0015 / 0

{
  "event_id": "KJ03JM25_Disassembly_A_004_ego__left__0015",
  "phase": "anomaly",
  "types": [
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the cylindrical tool body while the right hand used a wrench?",
  "answer": "I held the cylindrical tool body steady to stabilize it during the wrenching action.",
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

## KJ03JM25_Reassembly_A_002_ego__left__0006 / 0

{
  "event_id": "KJ03JM25_Reassembly_A_002_ego__left__0006",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the cylindrical metal body of the tool?",
  "answer": "I held the cylindrical metal body steady and maintained a firm grip on it.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Target hand is right, not left; left hand holds the body steady.",
      "No visible action on the cylindrical body beyond static holding; answer overstates activity."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## KJ03JM25_Reassembly_A_003_ego__right__0063 / 0

{
  "event_id": "KJ03JM25_Reassembly_A_003_ego__right__0063",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What did I do with the top screwdriver in the group?",
  "answer": "I grasped its handle and lifted it off the table surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Hand grasps a tool, but the specific 'top screwdriver' is not visually identifiable.",
      "Lifting the tool off the table surface is not shown in the provided frames."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE06AS03_Disassembly_A_001_ego__right__0032 / 0

{
  "event_id": "LE06AS03_Disassembly_A_001_ego__right__0032",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial"
  ],
  "qa_index": 0,
  "question": "What did I do with the screwdriver to loosen the fastener?",
  "answer": "I rotated the screwdriver handle to loosen the fastener.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "No visible rotation of the screwdriver handle is shown in the frames.",
      "No visible loosening of a fastener is demonstrated."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE06AS03_Disassembly_A_002_ego__right__0077 / 0

{
  "event_id": "LE06AS03_Disassembly_A_002_ego__right__0077",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What tool did I hold with my right hand?",
  "answer": "I held a screwdriver with a green and black handle.",
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

## LE06AS03_Disassembly_A_004_ego__left__0009 / 0

{
  "event_id": "LE06AS03_Disassembly_A_004_ego__left__0009",
  "phase": "anomaly",
  "types": [
    "spatial",
    "handling"
  ],
  "qa_index": 0,
  "question": "What did my left hand do with the angle grinder during the interval?",
  "answer": "It maintained a static grip on the angle grinder body to stabilize the tool.",
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

## LE06AS03_Disassembly_B_005_ego__right__0048 / 0

{
  "event_id": "LE06AS03_Disassembly_B_005_ego__right__0048",
  "phase": "anomaly",
  "types": [
    "spatial",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the screwdriver after rotating it against the silver component?",
  "answer": "I released the screwdriver and placed it on the table surface.",
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

## LE06AS03_Reassembly_A_003_ego__right__0140 / 0

{
  "event_id": "LE06AS03_Reassembly_A_003_ego__right__0140",
  "phase": "anomaly",
  "types": [
    "spatial",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the small black component using my right hand?",
  "answer": "I picked it up, moved it to the tool body, and placed it on the side.",
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

## LE07UF17_Disassembly_A_001_ego__right__0079 / 0

{
  "event_id": "LE07UF17_Disassembly_A_001_ego__right__0079",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the green-handled screwdriver tip?",
  "answer": "I positioned the tip against a screw on the black object and maintained steady contact.",
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

## LE07UF17_Disassembly_A_002_ego__right__0057 / 0

{
  "event_id": "LE07UF17_Disassembly_A_002_ego__right__0057",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "Where did I place the small black component with my right hand?",
  "answer": "I placed it into the second orange bin labeled 'Box 2'.",
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

## LE07UF17_Disassembly_A_003_ego__right__0043 / 0

{
  "event_id": "LE07UF17_Disassembly_A_003_ego__right__0043",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial"
  ],
  "qa_index": 0,
  "question": "What did I do with the screwdriver tip while holding the black component?",
  "answer": "I kept the screwdriver tip in contact with the black component on the table surface.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Video shows the screwdriver tip resting on the table, not in contact with the black component.",
      "Claim of contact contradicts visible gap between tool tip and component."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## LE07UF17_Reassembly_A_004_ego__right__0063 / 0

{
  "event_id": "LE07UF17_Reassembly_A_004_ego__right__0063",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the screwdriver on the instruction sheet?",
  "answer": "I grasped the screwdriver, lifted it vertically, and moved it away from the surface.",
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

## LE07UF17_Reassembly_B_005_ego__right__0047 / 0

{
  "event_id": "LE07UF17_Reassembly_B_005_ego__right__0047",
  "phase": "anomaly",
  "types": [
    "temporal",
    "handling"
  ],
  "qa_index": 0,
  "question": "What part of the angle grinder did I grasp with my right hand?",
  "answer": "I grasped the rear housing of the angle grinder.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Right hand contacts internal gears, not rear housing; specific part unsupported.",
      "No visual evidence of grasping rear housing in target interval."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## MA07LF04_Reassembly_A_002_ego__right__0159 / 0

{
  "event_id": "MA07LF04_Reassembly_A_002_ego__right__0159",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the small metal screw on the gray mat?",
  "answer": "I grasped the screw with my fingertips, lifted it, and held it in a pinch grip near the black tool.",
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

## MA07LF04_Reassembly_A_003_ego__left__0048 / 0

{
  "event_id": "MA07LF04_Reassembly_A_003_ego__left__0048",
  "phase": "anomaly",
  "types": [
    "temporal",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What object did I pick up from the orange bin with my left hand?",
  "answer": "I picked up a small metallic fastener from the bin labeled 'Box 3'.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Object picked is too small to visually identify as a fastener.",
      "Specific bin label 'Box 3' cannot be confirmed from the video."
    ],
    "decision": "revise"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## NA07GE21_Disassembly_A_001_ego__right__0157 / 0

{
  "event_id": "NA07GE21_Disassembly_A_001_ego__right__0157",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the screwdriver tip over the instruction sheet?",
  "answer": "I moved the screwdriver tip across the printed diagram on the sheet.",
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

## NA07GE21_Disassembly_A_003_ego__left__0007 / 0

{
  "event_id": "NA07GE21_Disassembly_A_003_ego__left__0007",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_part"
  ],
  "qa_index": 0,
  "question": "What did I do with the black motor housing using my left hand?",
  "answer": "I held the black motor housing steady on the table and maintained a static grip without releasing it.",
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

## NA07GE21_Reassembly_A_002_ego__right__0107 / 0

{
  "event_id": "NA07GE21_Reassembly_A_002_ego__right__0107",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the orange-handled screwdriver on the table?",
  "answer": "I grasped the screwdriver lying on the table and lifted it off the surface.",
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

## NA07GE21_Reassembly_A_004_ego__right__0067 / 0

{
  "event_id": "NA07GE21_Reassembly_A_004_ego__right__0067",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did my right hand do to the motor housing during the sequence?",
  "answer": "It held the motor housing steady and maintained a static gripping position on the motor body.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Question asks about right hand, but answer describes left hand holding the housing.",
      "Right hand is manipulating a small part, not holding the housing steady."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "0:unsupported_continuous_motion_claim"
  ],
  "strict_machine_pass": false
}

## SS07EL13_Disassembly_A_004_ego__right__0083 / 0

{
  "event_id": "SS07EL13_Disassembly_A_004_ego__right__0083",
  "phase": "anomaly",
  "types": [
    "spatial",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "Where did I place the wrench with my right hand?",
  "answer": "I placed the wrench onto the grey mat.",
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

## SS07EL13_Disassembly_B_005_ego__right__0059 / 0

{
  "event_id": "SS07EL13_Disassembly_B_005_ego__right__0059",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the tool body before inserting the screwdriver?",
  "answer": "I rotated the tool body to orient the side with the screw hole towards the camera.",
  "answerability": "visible",
  "review": {
    "qa_index": 0,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "No visible rotation of the tool body is shown in the target frames.",
      "No screwdriver insertion is visible; the tool is only held."
    ],
    "decision": "reject"
  },
  "structural_issues": [],
  "strict_machine_pass": false
}

## SS07EL13_Reassembly_A_002_ego__left__0005 / 0

{
  "event_id": "SS07EL13_Reassembly_A_002_ego__left__0005",
  "phase": "recovery",
  "types": [],
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

## SS07EL13_Reassembly_B_005_ego__left__0023 / 0

{
  "event_id": "SS07EL13_Reassembly_B_005_ego__left__0023",
  "phase": "anomaly",
  "types": [
    "temporal",
    "procedural"
  ],
  "qa_index": 0,
  "question": "What did I do with the black circular guard on the angle grinder?",
  "answer": "I pulled the guard away from the grinder, separating the components, and held it detached.",
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

## TO08CO25_Disassembly_A_002_ego__left__0026 / 0

{
  "event_id": "TO08CO25_Disassembly_A_002_ego__left__0026",
  "phase": "anomaly",
  "types": [
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What did I do with the screwdriver tip using my left hand?",
  "answer": "I inserted the screwdriver tip into a screw hole on the motor housing.",
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

## TO08CO25_Disassembly_A_002_ego__left__0026 / 1

{
  "event_id": "TO08CO25_Disassembly_A_002_ego__left__0026",
  "phase": "anomaly",
  "types": [
    "wrong_tool"
  ],
  "qa_index": 1,
  "question": "How did I manipulate the screwdriver handle with my left hand?",
  "answer": "I rotated the screwdriver handle to drive the screw.",
  "answerability": "visible",
  "review": {
    "qa_index": 1,
    "supported": false,
    "visually_answerable": false,
    "relevant_to_procedure": true,
    "answer_leakage": false,
    "duplicate": false,
    "issues": [
      "Rotation of handle not visible; only insertion shown.",
      "Claim of driving screw unsupported by visual evidence."
    ],
    "decision": "reject"
  },
  "structural_issues": [
    "1:duplicate_dimension"
  ],
  "strict_machine_pass": false
}

## TO08CO25_Disassembly_A_003_ego__left__0032 / 0

{
  "event_id": "TO08CO25_Disassembly_A_003_ego__left__0032",
  "phase": "anomaly",
  "types": [
    "temporal",
    "wrong_tool"
  ],
  "qa_index": 0,
  "question": "What object did my left hand grasp and lift from the table?",
  "answer": "My left hand grasped and lifted a green-handled screwdriver from the table surface.",
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

## TO08CO25_Disassembly_A_004_ego__left__0027 / 0

{
  "event_id": "TO08CO25_Disassembly_A_004_ego__left__0027",
  "phase": "anomaly",
  "types": [
    "temporal",
    "spatial"
  ],
  "qa_index": 0,
  "question": "What did I do with the small green object from the orange bin?",
  "answer": "I moved it from the bin to the grey mat and placed it on the surface.",
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

## TO08CO25_Reassembly_A_003_ego__left__0005 / 0

{
  "event_id": "TO08CO25_Reassembly_A_003_ego__left__0005",
  "phase": "anomaly",
  "types": [
    "handling"
  ],
  "qa_index": 0,
  "question": "What did I do with the drive shaft using my left hand?",
  "answer": "I maintained a static grip on the drive shaft throughout the sequence.",
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

## TO08CO25_Reassembly_A_004_ego__left__0059 / 0

{
  "event_id": "TO08CO25_Reassembly_A_004_ego__left__0059",
  "phase": "normal",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the screwdriver tip on the black component?",
  "answer": "I inserted the screwdriver tip into a screw slot on the black component.",
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

## TO08CO25_Reassembly_B_005_ego__left__0019 / 0

{
  "event_id": "TO08CO25_Reassembly_B_005_ego__left__0019",
  "phase": "recovery",
  "types": [],
  "qa_index": 0,
  "question": "What did I do with the metallic housing using my left hand?",
  "answer": "I held the metallic housing steady to stabilize the object.",
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
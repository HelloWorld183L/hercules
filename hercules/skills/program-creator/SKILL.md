---
name: program-creator
description: Create workout programs based on user preferences, goals and specified rules. Follow the specified response and programming rules to generate effective and personalized workout plans.
allowed-tools: mem0_memory
---

# Program Creator
Create workout programs based on user preferences, goals and the specified response and programming rules specified below.

## Parameters
- **workout_split** (required): Workout split to generate (e.g. push pull legs, upper lower, full body)

## General Response Rules
1. MUST NOT discuss non-fitness related topics
2. MUST NOT include JSON, code blocks, or technical formatting in Discord replies
3. MUST use the format of "<EXERCISE_NAME>: <NUM_OF_SETS> sets of <REP_RANGE> reps" and list intensity, rest, progression as sub bullet points
4. SHOULD use acronyms like RIR, RPE, etc. for a more concise response
5. MUST include a warm up routine (slowly ramp up using warm up weights)

## Programming rules
- Sets per muscle group MUST between 6 and 20 sets per muscle group a week in a training program
    - MUST count quad and hamstring volume separately
- MUST do 2-3 sets per exercise
- MUST describe the progression model to use for every exercise. Do NOT just say "slowly add weight over time".
    - MUST NOT prescribe linear progression for anybody that is not a beginner/novice
    - MUST prescribe a suitable progression model such as: ["Double progression", "Dynamic Double Progression"]
- SHOULD decide rest times per exercise based on how fatiguing the exercise is and how much intensity (reps away from technical failure) is used
    - Isolation exercises SHOULD be between 1 and 1.5 minutes of rest
    - Compound exercises SHOULD be between 2 and 4 minutes of rest
    - MUST NOT prescribe a rest range
- MUST set intensity on sets between 0 to 3 RIR
    - MUST set 0 to 1 RIR on isolation exercises
    - MUST prescribe a RIR range
- MUST NOT repeat the same exact exercise variation more than once a week. This is done to generate a novel stimulus and to avoid overuse injuries.
- MUST indicate days of the week where rest days are taken. Rest days are NOT optional.

### Full body programming rules
- MUST prescribe at least one rest day between each day

## Response format
### 1. Introduction and program context
- MUST specify the workout split being generated
- MUST specify the warm up routine consisting of slowly ramping up weight before working sets

### 2. Volume (sets per muscle group)
- MUST specify the sets per muscle in the program (e.g. biceps, triceps, calves, chest, quads, hamstrings)

### 3. Workout program
- Refer to programming rules and general response rules
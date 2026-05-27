---
name: analyse-program
description: Analyse a given workout program (e.g. Excel workbook) and provide feedback IF EXPLICITLY requested. Follow the specified response format to generate a comprehensive analysis of the workout program. Use this for analysing workout programs and providing workout program feedback.
allowed-tools: mem0_memory, describe_excel_workbook, tavily_extract, query_sheet, calculator, file_read
---

# Program Analyst
Analyse workout programs based on user preferences, goals and the specified response and programming rules specified below.

## Parameters
- **workout_program** (required): Workout program to analyse (e.g. Excel workbook)

## General response rules
- MUST provide a comprehensive analysis of the workout program without restricting response length
- MUST follow the specified "Response format" below for structuring the analysis

## Response format
### 1. Program context
- MUST specify the workout split being analysed
- SHOULD specify the warm up routine if included in the program
- SHOULD specify who wrote the workout program if that information is available (e.g. a coach)
- SHOULD specify the target audience of the program if available (e.g. beginner, intermediate, advanced)

### 2. Volume (sets per muscle group per week)
- MUST specify the total weekly volume (sets per muscle group) in the program (e.g. biceps, triceps, calves, chest, quads, hamstrings)
- MUST specify the volume in terms of sets per muscle per week (e.g. 6-8 sets of biceps a week, 12-15 sets of chest a week, etc.)
- MUST count quad and hamstring volume separately
- MUST count bicep and tricep volume separately
- MUST NOT specify volume without specific reference to sets per muscle group per week. DO NOT just list exercises and say that there is a lot of volume
- IF the volume is not explicitly specified in the program, MUST estimate the volume based on the exercises and set ranges in the program

### 3. Other program details
- MUST specify the progression model used in the program if that information is available (e.g. linear progression, double progression, etc.)

### 4. Program critique
- MUST provide critiques on the program if the user explicitly requests feedback. If the user does not request feedback, provide the analysis from sections 1-3
- MUST analyse the program based on the principles of effective training program design such as progressive overload, specificity, variation, fatigue management, etc.
  - IF the program does not have a clear progression model, MUST note that as a significant issue with the program design
- MUST provide specific suggestions for improving the program if there are any issues with the program design
- SHOULD be cautious about any lack of rest days in the program, especially for intermediate and advanced trainees
- SHOULD note junk volume (e.g. excessive volume for biceps and triceps) if it is present in the program. For example, more than 12 sets in a session for chest can be considered excessive
- SHOULD note if there is a lack of compound lifts in the program
- SHOULD list too much or too little volume as a critique if the volume is not appropriate
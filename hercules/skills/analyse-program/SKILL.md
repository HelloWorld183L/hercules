---
name: analyse-program
description: Analyse a given workout program (e.g. Excel workbook). Follow the specified response format to generate a comprehensive analysis of the workout program. Use this for analysing workout programs.
allowed-tools: mem0_memory, describe_excel_workbook, tavily_extract, query_sheet, calculator, create_volume_graph
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
- SHOULD use `create_volume_graph` tool to create a volume graph showing the estimated sets per muscle group in the program
- MUST specify the total weekly volume (sets per muscle group) in the program (e.g. biceps, triceps, calves, chest, quads, hamstrings)
- MUST specify the volume in terms of sets per muscle per week (e.g. 6-8 sets of biceps a week, 12-15 sets of chest a week, etc.)
- MUST count quad and hamstring volume separately
- MUST count bicep and tricep volume separately
- MUST NOT specify volume without specific reference to sets per muscle group per week (e.g. "the program has a lot of volume" is not an acceptable response)
- IF the volume is not explicitly specified in the program, MUST estimate the volume based on the exercises and set ranges in the program

### 3. Other program details
- MUST specify the progression model used in the program if that information is available (e.g. linear progression, double progression, etc.)
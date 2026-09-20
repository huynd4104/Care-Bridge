# Expert Consultation & Care Plan Adjustment Workflow — Step Description

| Field | Value |
|---|---|
| Diagram | `main work flow-5. Expert Consultation Workflow.drawio` / `mainworkflow-Trang-3.drawio` (Page 3) |
| Folder | `03_Design/Workflow/` |
| Diagram type | Activity / Swimlane workflow |
| Swimlanes | Mother (User), CareBridge System, Verified Healthcare Expert |
| Relevant Use Cases | `UC-EX-07` (Browse Expert), `UC-EX-08` (Manage Request), `UC-EX-09` (Process Request), `UC-EX-10` (Direct Messages), `UC-EX-11` (Direct Calls), Maternal Checklist & Care Plan Adjustment |
| Purpose | Describes the end-to-end workflow: a mother creates a consultation request, the expert reviews and accepts or rejects it. Upon acceptance, the system initializes a Direct Conversation for chat and video calls. The expert then inspects shared maternal health records and checklist, prescribes/adjusts custom care tasks with clinical notes, which are synchronized to the mother's daily schedule for execution. |

## Description

| # | Step Name | Detail Description | Role | Note |
|---|---|---|---|---|
| 1 | Select Expert & Submit Consultation Request | The mother browses verified healthcare specialists, chooses an expert, specifies preferred consultation time window, enters symptoms and medical questions, and submits the consultation request. | Mother | Entry point of the expert consultation workflow; initiated from the specialist directory or AI Nurse triage referral. |
| 2 | Save Request (PENDING) & Notify Assigned Expert | The system creates and persists the consultation request record with status PENDING, and sends a real-time notification alert to the designated doctor. | System | Initial request status is set to PENDING awaiting specialist triage and decision. |
| 3 | Review Pending Request & Inspect Patient Context & Triage | The doctor opens their assigned consultation queue, reviews the patient's submitted notes, health profile, trimester stage, and initial triage assessment. | Expert | Doctor evaluates clinical urgency, medical relevance, and schedule availability before deciding. |
| 4 | Accept Request? | The doctor decides whether to accept the consultation request to proceed with care, or decline it. | Expert | Decision point: Yes branches to Step 5 (Acceptance); No branches to Step 4A (Rejection). |
| 4A | Reject Request with Reason | The doctor declines the request and enters a clear clinical or scheduling reason for the rejection. | Expert | Provides transparent feedback to the mother regarding why the request could not be fulfilled. |
| 4B | Update Status to REJECTED & Notify Mother | The system updates the consultation request status to REJECTED, stores the rejection rationale, and delivers a notification to the mother. | System | Terminal step for declined requests. The mother may select another available specialist. |
| 5 | Update Status to ACCEPTED & Auto-Create Direct Conversation Room | The system transitions the request status to ACCEPTED and automatically provisions a private Direct Conversation room for teleconsultation. | System | Initializes the real-time communication channel and enables direct messaging and audio/video calling. |
| 6 | Conduct Direct Consultation Session (Chat / Video Call) | The mother and doctor participate in teleconsultation via encrypted real-time chat, sharing vital metric cards, baby milestone summaries, or 1-on-1 audio/video calling. | Mother / Expert | Teleconsultation session supports real-time WebSocket messaging and ZegoCloud WebRTC audio/video call. |
| 7 | Inspect Shared Records & Adjust Care Plan | The doctor accesses the mother's shared maternal health records, pregnancy metrics, and daily checklist, then adds custom doctor-prescribed tasks with clinical advice. | Expert | Doctor inspects shared metrics and customizes care plan tasks with clinical guidance and scheduled reminders. |
| 8 | Synchronize Doctor-Prescribed Tasks to Mother's Schedule | The system validates doctor-prescribed tasks, tags them with clinical origin, and synchronizes them into the mother's active daily schedule and reminder engine. | System | Synchronizes doctor-adjusted tasks, timings, and clinical notes directly into mother's active daily checklist. |
| 9 | Receive & Apply Updated Care Plan | The mother views the doctor's clinical recommendations and approved care tasks, executing them as part of her daily maternal wellness routine. | Mother | Mother integrates doctor-approved tasks into daily routine; loops back to Maternal Care Plan Workflow (Figure 3, Step 6). |
| Boundary | Workflow Boundary | Expert consultation is strictly conducted between verified healthcare practitioners and mothers with active care plans. All medical adjustments require explicit doctor authorization and are synchronized directly to patient routines. | System | Enforces medical data privacy, professional credential verification, and traceable clinical record keeping across CareBridge. |

## Role Legend

| Role | Meaning |
|---|---|
| Mother | The maternal user who creates consultation requests, participates in direct chat/video calls, and executes the updated doctor-prescribed care plan in her daily routine. |
| System | The CareBridge platform, which persists requests, provisions Direct Conversation rooms, routes real-time signaling/messaging, and synchronizes doctor tasks into maternal schedules. |
| Expert | A verified healthcare professional who evaluates consultation requests, conducts teleconsultations, reviews shared records, and tailors daily care tasks with clinical notes. |

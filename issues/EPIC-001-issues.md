# EPIC-001: Mobile-First Frictionless Capture - GitHub Issues Breakdown

## Issue #1: [Mobile] iOS Shortcuts MVP for Voice Capture
**Priority**: High  
**Effort**: M (3-5 days)  
**Labels**: `mobile`, `mvp`, `ios-shortcuts`, `epic-001`

### Why This Matters
- Eliminates Mac dependency for 80% of use cases
- Zero app installation required (Shortcuts is built-in)
- Proves the concept before investing in native app
- Immediate value delivery to users

### Acceptance Criteria
- [ ] iOS Shortcut captures voice recording via native memo app
- [ ] Shortcut transcribes audio using iOS native speech recognition
- [ ] Transcribed text uploaded directly to S3 `transcripts/unclassified/` folder
- [ ] Success/failure feedback shown to user
- [ ] Works on iOS 16+ devices
- [ ] Shortcut is shareable via iCloud link

### Technical Requirements
- Use iOS Shortcuts app (no coding required initially)
- Leverage "Dictate Text" action for transcription
- "Get Contents of URL" action for S3 presigned URL upload
- Store AWS credentials securely in Shortcuts (or use presigned URLs)
- JSON payload format: `{timestamp, transcript, device_id, ios_version}`

### Testing Scenarios
**Happy Path:**
1. User taps shortcut → records 30-second memo → sees "Uploaded successfully"
2. Transcript appears in S3 within 10 seconds
3. Lambda processes unclassified transcript

**Edge Cases:**
- No internet connection → Queue locally (manual retry for MVP)
- Recording over 5 minutes → Truncate or split
- Background noise → User sees transcription before upload
- Accidental activation → Cancel button available

### Dependencies
- None (can start immediately)

### Definition of Done
- [ ] Shortcut published and tested on 3+ devices
- [ ] Documentation with installation instructions
- [ ] S3 bucket configured for mobile uploads
- [ ] Basic CloudWatch metrics for mobile uploads

---

## Issue #2: [Mobile] S3 Direct Upload with Presigned URLs
**Priority**: High  
**Effort**: S (1-2 days)  
**Labels**: `mobile`, `backend`, `security`, `epic-001`

### Why This Matters
- Secure uploads without embedding AWS credentials in shortcuts
- Enables any mobile client to upload safely
- Foundation for offline queue management
- Reduces Lambda cold starts (no proxy needed)

### Acceptance Criteria
- [ ] Lambda function generates presigned S3 upload URLs
- [ ] URLs expire after 5 minutes
- [ ] URLs restricted to specific content types (text/json)
- [ ] Size limit enforced (max 1MB per transcript)
- [ ] CORS configured for mobile browsers
- [ ] API Gateway endpoint: `GET /upload-url`

### Technical Requirements
- Lambda function using boto3 `generate_presigned_url()`
- API Gateway with no auth required (URLs are time-limited)
- S3 bucket policy restricting upload paths
- CloudFormation/CDK updates for new resources
- Response format: `{upload_url, expires_at, max_size}`

### Testing Scenarios
**Happy Path:**
1. Request URL → Upload file → File appears in S3
2. Multiple simultaneous uploads work

**Edge Cases:**
- Expired URL → 403 Forbidden response
- Oversized file → Upload rejected
- Wrong content type → Upload rejected
- Malicious path injection → Blocked by policy

### Dependencies
- None

### Definition of Done
- [ ] API endpoint deployed and tested
- [ ] iOS Shortcut updated to use presigned URLs
- [ ] Security review passed
- [ ] API documentation written

---

## Issue #3: [Mobile] Post-Recording Classification UI
**Priority**: High  
**Effort**: L (5-8 days)  
**Labels**: `mobile`, `frontend`, `ux`, `epic-001`

### Why This Matters
- Removes cognitive load during recording ("just speak")
- Enables batch classification of multiple recordings
- Better UX than folder selection
- Allows for ML-assisted classification later

### Acceptance Criteria
- [ ] Web UI accessible from mobile Safari/Chrome
- [ ] Lists unclassified transcripts from last 24 hours
- [ ] Swipe/tap to classify: Work, Memory, GitHub Idea, Delete
- [ ] Bulk actions for multiple transcripts
- [ ] Visual preview of transcript content (first 100 chars)
- [ ] Successfully classified items move to correct S3 path

### Technical Requirements
- Mobile-first React/Vue app (or simple vanilla JS)
- Hosted on S3 + CloudFront
- API Gateway endpoints for listing/classifying
- DynamoDB table for classification queue
- Responsive design for iPhone/Android
- PWA manifest for "Add to Home Screen"

### Testing Scenarios
**Happy Path:**
1. Record 3 memos → Open classifier → Swipe to classify → Agents process

**Edge Cases:**
- 50+ unclassified items → Pagination works
- Offline classification → Syncs when online
- Accidental classification → Undo button for 5 seconds
- Multiple devices → No duplicate processing

### Dependencies
- Issue #2 (presigned URLs)

### Definition of Done
- [ ] Mobile UI deployed and accessible
- [ ] Classification moves files in S3
- [ ] 5+ users tested on real devices
- [ ] Performance: <2s load time on 4G

---

## Issue #4: [Mobile] Offline Recording Queue with Sync
**Priority**: Medium  
**Effort**: L (5-8 days)  
**Labels**: `mobile`, `offline`, `ios-shortcuts`, `epic-001`

### Why This Matters
- Voice memos often happen without internet (subway, airplane, hiking)
- Prevents data loss from failed uploads
- Better user experience with automatic retry
- Foundation for native app features

### Acceptance Criteria
- [ ] Shortcuts saves recordings locally when offline
- [ ] Queue automatically syncs when connection restored
- [ ] User sees queue status (3 pending uploads)
- [ ] Failed uploads retry with exponential backoff
- [ ] Old recordings (>7 days) auto-delete from queue

### Technical Requirements
- iOS Shortcuts local storage (files/notes)
- Queue format: JSONL with metadata
- Background sync via Shortcuts automation
- Status widget showing queue size
- Error tracking for failed uploads

### Testing Scenarios
**Happy Path:**
1. Airplane mode → Record 5 memos → Enable WiFi → All sync within 1 minute

**Edge Cases:**
- 100+ queued items → Sync in batches
- Corrupt queue file → Graceful recovery
- Storage full → User warning
- Partial upload → Resume from last successful

### Dependencies
- Issue #1 (iOS Shortcuts MVP)
- Issue #2 (presigned URLs)

### Definition of Done
- [ ] Offline queue implemented in Shortcuts
- [ ] Auto-sync tested in real conditions
- [ ] Queue monitoring in CloudWatch
- [ ] User documentation for offline mode

---

## Issue #5: [Mobile] Push Notifications for Processing Status
**Priority**: Medium  
**Effort**: M (3-5 days)  
**Labels**: `mobile`, `notifications`, `sns`, `epic-001`

### Why This Matters
- Users know their memo was processed successfully
- Immediate feedback loop encourages usage
- Error notifications prevent data loss
- Enables two-way interaction (future)

### Acceptance Criteria
- [ ] SNS configured for iOS push notifications
- [ ] Users can opt-in via shortcut setup
- [ ] Notifications show: "Work memo logged" or "GitHub repo created"
- [ ] Error notifications for failed processing
- [ ] Notification includes link to output (S3 presigned URL)
- [ ] Daily summary notification (optional)

### Technical Requirements
- AWS SNS with iOS platform application
- Lambda updates to publish notifications
- Notification templates for each agent type
- User preference storage (DynamoDB)
- APNS certificate configuration

### Testing Scenarios
**Happy Path:**
1. Record memo → Process → Receive notification in <30 seconds

**Edge Cases:**
- Notifications disabled → Silent success
- Multiple memos → Grouped notifications
- Do not disturb → Respect iOS settings
- Network timeout → Notification eventually delivered

### Dependencies
- Issue #1 (iOS Shortcuts MVP)
- Existing Lambda infrastructure

### Definition of Done
- [ ] SNS configured and tested
- [ ] Notifications working on 3+ devices
- [ ] opt-in/opt-out flow documented
- [ ] Notification metrics in CloudWatch

---

## Issue #6: [Mobile] Progressive Web App for Enhanced Features
**Priority**: Low  
**Effort**: XL (10-15 days)  
**Labels**: `mobile`, `pwa`, `frontend`, `epic-001`

### Why This Matters
- Richer UI than iOS Shortcuts allows
- Cross-platform (Android support)
- Installable without app store
- Foundation for future native features

### Acceptance Criteria
- [ ] PWA installable on iOS/Android home screen
- [ ] Voice recording with waveform visualization
- [ ] Real-time transcription preview
- [ ] Classification happens in-app
- [ ] Recent recordings history
- [ ] Offline support with service worker
- [ ] Push notification integration

### Technical Requirements
- React/Vue/Svelte PWA framework
- Web Audio API for recording
- Service Worker for offline
- IndexedDB for local storage
- Web Push API integration
- HTTPS required (CloudFront)

### Testing Scenarios
**Happy Path:**
1. Install PWA → Record → Classify → View history

**Edge Cases:**
- iOS PWA limitations → Graceful degradation
- Microphone permissions → Clear instructions
- Large recordings → Chunked upload
- Background recording → Not supported (document limitation)

### Dependencies
- Issues #2, #3, #5 (infrastructure ready)

### Definition of Done
- [ ] PWA deployed and installable
- [ ] Feature parity with shortcuts + more
- [ ] Performance: <3s initial load
- [ ] 10+ user beta test completed
- [ ] Analytics integration

---

## Issue #7: [Mobile] Smart Classification ML Service
**Priority**: Low  
**Effort**: L (5-8 days)  
**Labels**: `mobile`, `ml`, `backend`, `epic-001`

### Why This Matters
- Reduces classification burden on users
- Learns from user patterns over time
- Enables fully automatic pipeline
- Better UX for power users

### Acceptance Criteria
- [ ] ML model suggests classification with confidence score
- [ ] Suggestions based on keywords and patterns
- [ ] User can accept/reject suggestions
- [ ] Model improves from user feedback
- [ ] Auto-classify when confidence >90%
- [ ] Weekly model retraining

### Technical Requirements
- SageMaker endpoint for inference
- Training pipeline in Lambda/Batch
- Feature extraction from transcripts
- DynamoDB for training data
- A/B testing framework
- Model versioning in S3

### Testing Scenarios
**Happy Path:**
1. Record work memo → 95% confidence → Auto-classified correctly

**Edge Cases:**
- Ambiguous content → Show multiple suggestions
- New classification type → Model adapts
- Privacy mode → Disable ML for sensitive content
- Model drift → Automatic retraining triggered

### Dependencies
- Issue #3 (classification UI for training data)
- 1000+ classified transcripts for training

### Definition of Done
- [ ] ML pipeline deployed
- [ ] 80%+ accuracy on test set
- [ ] User feedback mechanism
- [ ] Model monitoring dashboard
- [ ] Privacy documentation

---

## Implementation Roadmap

### Phase 1: MVP (Issues #1, #2)
- iOS Shortcuts with S3 upload
- Basic functionality, no Mac required
- Timeline: 1 week

### Phase 2: Enhanced UX (Issues #3, #4)
- Classification UI
- Offline support
- Timeline: 2-3 weeks

### Phase 3: Engagement (Issue #5)
- Push notifications
- Feedback loop
- Timeline: 1 week

### Phase 4: Next Generation (Issues #6, #7)
- PWA for richer features
- ML-powered classification
- Timeline: 3-4 weeks

## Success Metrics
- 50% reduction in Mac transcription usage within 1 month
- 90% of recordings successfully processed without manual intervention
- <30 second average time from recording to classification
- 80% user retention after 30 days
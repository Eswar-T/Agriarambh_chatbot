# M10 — Community Hub

| | |
|---|---|
| **Status** | 🟡 Partial — the social feed (posts, likes, saves, comments, polls, voice, blogs, stories) is **live** on Supabase. Learn/News/Techniques/Questions pages, rewards, contributors, referral and spotlight are **mock** |
| **Roles** | Farmer, Owner |
| **Code** | `src/navigation/HubStack.tsx`, `src/screens/hub/**` (`HubScreen`, `MyPostsScreen`, `components/community/*`, `hooks/{useCommunityHub,useComments,useMyPosts}`, `utils/{communityApi,mediaRules}`, `constants/{communityData,mediaSources}`), legacy pages `src/screens/{LatestNews,NewsDetail,ModernFarmingTech,CommunityQuestions,QuestionDetail,CreatePost,FilterByCrop}Screen.tsx`, `src/constants/hubMockData.ts`, `src/components/hub/*` |
| **DB** | `posts`, `post_likes`, `post_saves`, `comments`, `stories`, `poll_votes`; RPC `toggle_post_like`, `cast_poll_vote`; buckets `post-media`, `stories` |
| **Related** | [M14 Notifications](M14-notifications.md), [M15 Legal](M15-settings-localization-legal.md) |

## 1. Purpose & scope
A farmer-to-farmer feed to share success stories, techniques and questions, learn from short guides, and stay engaged (rewards, referrals).

## 2. Features

| ID | Feature | Status | Notes |
|----|---------|:------:|-------|
| M10-F01 | Feed with **category chips** (All, Success, Vermicompost, Organic, Tips, Pest control, Questions) and **post-type filter** (photo, video, blog, poll, voice) | ✅ | `posts` |
| M10-F02 | Create post: text, photo(s), video, **voice note**, **blog** (title + long body), **poll** | ✅ | Composer + `PostComposerModal`; poll via `poll_options` |
| M10-F03 | Media rules: video **10–15 s**, voice **≤ 60 s**, photos compressed at pick-time; clear messages when violated | ✅ | `MEDIA_RULES`, `mediaRules.ts`; byte limits currently `Infinity` |
| M10-F04 | Like (atomic RPC, optimistic UI) and Save | ✅ | `toggle_post_like`; `post_saves` |
| M10-F05 | Comments modal: add, edit, delete; counter kept by DB trigger | ✅ | `useComments` |
| M10-F06 | Poll voting with live tallies and "my vote" | ✅ | `cast_poll_vote` |
| M10-F07 | Delete own post | ✅ | |
| M10-F08 | **My Posts** | ✅ | `useMyPosts` |
| M10-F09 | **Stories** (24 h, image/video, max 3/day, own-only today); expired rows and files purged on open | 🟡 | `stories`; no multi-author tray yet |
| M10-F10 | Inline media player, blog reader, linkified text | ✅ | |
| M10-F11 | Verified badge, role chip, author avatar tone | 🟡 | `verified` and badge logic are decorative/mock |
| M10-F12 | **Learn strip / guides**, **Spotlight**, **Top contributors**, **Kisan Rewards**, **Refer & Earn** | 🧪 | `communityData.ts` constants; `rewards` table exists but unused |
| M10-F13 | Latest News, News Detail, Modern Farming Tech, Community Questions + Question Detail, Filter by Crop (mandi sample) | 🧪 | `hubMockData.ts` |
| M10-F14 | Mock mode: posting works in memory only (no persistence); there is no seeded feed, so it starts empty | 🧪 | `communityApi.enabled` is false without Supabase |
| M10-F15 | Report / block / moderate content | ⚪ | **Required for store approval of user-generated content** |
| M10-F16 | Follow farmers, notifications on likes/comments/replies | ⚪ | |
| M10-F17 | Search posts | ⚪ | |
| M10-F18 | Expert Q&A: verified agronomist answers, "best answer" | ⚪ | Mock page exists |

## 3. Flows
* **Post:** Hub → "Create post" row / composer → choose type → pick media (camera or gallery; mic for voice) → rule check → upload to `post-media` (path `<userId>/…`) → insert `posts` → feed refresh.
* **Like:** tap → optimistic flip → RPC → reconcile with server result; failure rolls back.
* **Story:** tap "+" → pick media → upload to `stories` → insert with `expires_at = now + 24h`; on opening the Hub, `purgeExpiredStories()` deletes the row **and** the storage file.

## 4. Screens and routes (`HubStackParamList`)
`Hub` (root) · `MyPosts` · `FilterByCrop` · `LatestNews` · `NewsDetail {id,title}` · `ModernFarmingTech` · `CommunityQuestions` · `QuestionDetail {id}` · `CreatePost {from?}` · `NotificationsCenter` · `Settings`.

## 5. Data model
`posts(author_id, category, title, text, media_type, media_urls[], earned_label, likes_count, comments_count, poll_options, created_at)`. `media_type` values used by the app: `image, video, grid, text, blog, audio, poll`. **Repo SQL enum lacks `poll`** (and `poll_options`, `poll_votes`) — part of DB-1.

## 6. Business rules
1. Anyone signed in can read; only the author can edit/delete a post; comments editable/deletable by their author.
2. Counters (`likes_count`, `comments_count`) are changed **only** by the RPC/trigger — never from the client.
3. A user has at most one like, one save, and one vote per poll post.
4. Voice ≤ 60 s; video 10–15 s; stories ≤ 3 per user per day and expire in 24 h.
5. All uploads must use `<userId>/…` object paths or storage RLS rejects them.
6. Feed shows relative times ("Just now", "5m ago", "Yesterday").

## 7. Known issues & tech debt

| ID | Issue | Fix |
|----|-------|-----|
| M10-D1 | **No content reporting, blocking or moderation** → store-policy risk (UGC) | M10-T1 (P0 for launch) |
| M10-D2 | Public buckets + no size caps (`maxBytes: Infinity`) → abuse and cost | Set caps (e.g. photo 2 MB after compression, video 15 MB) and server-side limits |
| M10-D3 | Authors' avatars are generated tones; `profiles.avatar_url` not used in feed | Use real avatars |
| M10-D4 | `fetchPosts` loads the whole feed (no pagination) | Cursor pagination (M10-T4) |
| M10-D5 | Mixed architecture: new feed is well structured; legacy pages (`LatestNews…`) are flat mock screens | Migrate or remove |
| M10-D6 | Likes by public `post_likes` read policy reveal who liked what | Acceptable; review privacy text |
| M10-D7 | Rewards, streaks, referral are display-only | Define rules before building |
| M10-D8 | Stories: own-only, so the tray has no social value | Show followed/nearby farmers' stories |

## 8. Implementation plan

| Phase | Task | ID | Pri | Size | Acceptance criteria |
|-------|------|----|:---:|:----:|---------------------|
| 1 | **Report post/comment/story + block user**; `reports` table; Admin portal queue; hide reported-by-me content instantly | M10-T1 | P0 | L | Report from any item; blocked user's content disappears; Admin can action |
| 1 | Media limits (client + storage policy); compress video where possible | M10-T2 | P0 | M | Over-limit upload rejected with message |
| 1 | Add poll migration (`poll` enum value, `poll_options`, `poll_votes`, `cast_poll_vote`) to repo | M10-T3 | P0 | S | Fresh DB supports polls |
| 2 | Pagination + pull-to-refresh + "new posts" pill; realtime for new posts | M10-T4 | P1 | M | 20 per page; smooth scroll |
| 2 | Real avatars and role/verified badge from `profiles` (Admin-set `verified`) | M10-T5 | P1 | S | Badge only for Admin-verified users |
| 2 | Notifications: like/comment/reply via triggers ([M14](M14-notifications.md)) | M10-T6 | P1 | M | Author notified; mute option |
| 2 | Replace mock News/Techniques with real sources (reuse `newsApi`/`videosApi`) | M10-T7 | P2 | M | No `hubMockData` imports remain |
| 2 | Expert Q&A: question type with accepted answer and expert badge | M10-T8 | P2 | L | |
| 3 | Follow system + following feed + multi-author stories | M10-T9 | P2 | L | |
| 3 | Rewards v1 (coins for posts/comments, streaks) with anti-abuse rules; referral codes | M10-T10 | P2 | L | Ledger table; caps per day |
| 3 | Post search & hashtags / crop tags | M10-T11 | P2 | M | |

## 9. Test checklist
- [ ] Post each type (text, photo, video, voice, blog, poll) and see it after restart
- [ ] 16 s video rejected; 9 s rejected; 61 s voice rejected
- [ ] Two phones: like count is exact after both like at once
- [ ] Edit/delete someone else's comment is impossible (raw API)
- [ ] Story disappears after 24 h and its file is gone from storage
- [ ] Offline: composer keeps draft; error shown on send
- [ ] Mock mode: feed starts empty, posting works in memory, nothing persists after restart

## 10. Definition of Done
Standard DoD plus: UGC safety checks (report/block path works) and moderation runbook agreed with Operations.

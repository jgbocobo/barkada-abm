/**
 * digital_payment_adoption.gaml
 *
 * Agent-Based Model: Digital Payment Adoption Among UPLB Students
 *
 * This simulation models how GCash/Maya spreads among 1,000 university
 * students over one semester (15 weeks = 105 days). Each student is an
 * agent who decides whether to adopt based on ads, peer pressure, trust,
 * and their personality type. Students are connected through organizations,
 * friendships, and shared classes.
 *
 * Author:  Jorge Bocobo
 * Created: 2026-02-07
 */

model digital_payment_adoption

global {

	// ── How many students and how long the simulation runs ─────
	int M <- 1000;    // total number of student agents on campus
	int T <- 105;     // one semester = 15 weeks x 7 days

	// ── Bass diffusion: the two forces that drive adoption ────
	// p_ad = chance per day that an ad makes an Unaware student hear about GCash
	// p_wom = total word-of-mouth pressure (divided by connections later so denser networks aren't unfairly stronger)
	float p_ad  <- 0.003;
	float p_wom <- 0.08;

	// ── How students progress through adoption stages ─────────
	// A student must use GCash for 7 days before becoming a Regular user.
	// After convincing 3 people, they become an Advocate (1.5x more influential).
	int   t_trial    <- 7;
	int   n_advocate <- 3;
	float c_advocate <- 1.5;

	// ── Decision thresholds ───────────────────────────────────
	// b_threshold: how convinced a student needs to be before trying GCash (0 = easy, 1 = impossible)
	// r_threshold: if a student's trust in the platform is below this, they refuse no matter what
	float b_threshold <- 0.35;
	float r_threshold <- 0.3;

	// ── Network overlap ───────────────────────────────────────
	// 30% chance that an org connection also appears in the friend layer
	// (because your org-mate is often also your friend)
	float p_overlap <- 0.3;

	// ── Simulation mode switches ──────────────────────────────
	// baseline_mode: true = simple Bass validation (all agents identical, one dense network)
	//                false = full model with personas, multiplex network, BDI decisions
	// is_batch: true when running automated experiments (disables GUI pause)
	// experiment_id: tells the CSV export which experiment is running
	// empirical_mode: true = Stage C validation (100 agents from real survey + 300 synthetic, M=400)
	bool baseline_mode <- true;
	bool is_batch <- false;
	string experiment_id <- "";
	bool empirical_mode <- false;
	string empirical_cohort_file <- "../../data/empirical_cohort.csv";
	int nb_empirical <- 100;        // real-survey-derived agents
	int nb_synthetic <- 300;        // equal-persona synthetic agents
	// Map persona name (from CSV) to internal 1-5 index
	map<string, int> persona_name_to_idx <- [
		"Tech Enthusiast"::1,
		"Social Follower"::2,
		"Cautious Adopter"::3,
		"Price Sensitive"::4,
		"Disengaged"::5
	];

	// ── How strongly each type of connection influences you ───
	// Org-mate (0.8): strong — you see them every meeting
	// Friend (0.5): medium — casual friend you hang out with sometimes
	// Classmate (0.2): weak — someone you barely talk to in class
	// Best friend (0.95): barkada — your closest circle
	float w_org    <- 0.8;
	float w_friend <- 0.5;
	float w_class  <- 0.2;
	float w_best   <- 0.95;

	// ── The 5 student personality types ───────────────────────
	// Each row: [trust_in_platform, peer_susceptibility, price_fairness, ad_receptivity, engagement, personal_threshold]
	// These values come from synthetic survey data and will be replaced with real survey results.
	list<list<float>> persona_profiles <- [
		[0.8, 0.4, 0.7, 0.8, 0.9, 0.15],   // Tech Enthusiast: trusts GCash, not easily swayed by peers, loves tech
		[0.5, 0.9, 0.6, 0.5, 0.5, 0.25],   // Social Follower: does what friends do, moderate trust
		[0.3, 0.5, 0.7, 0.4, 0.4, 0.45],   // Cautious Adopter: skeptical, needs lots of convincing
		[0.6, 0.6, 0.3, 0.6, 0.6, 0.35],   // Price Sensitive: cares about fees and value
		[0.5, 0.3, 0.5, 0.3, 0.2, 0.55]    // Disengaged: doesn't care, hard to reach
	];
	// Equal split: 200 students of each type
	list<float> persona_proportions <- [0.2, 0.2, 0.2, 0.2, 0.2];
	int nb_orgs <- 20;       // 20 student organizations (~50 members each)
	int nb_colleges <- 7;    // 7 colleges at UPLB

	// ── Campus events that boost advertising ─────────────────
	// During these events, the chance of seeing an ad is multiplied.
	// Format: [start_day, end_day, multiplier]
	list<list> campus_events <- [
		[1, 5, 2.0],       // Registration Week: 2x more ads (posters everywhere)
		[30, 32, 3.0],     // University Fair: 3x (GCash booths, promos)
		[50, 55, 1.5],     // Midterm Week: 1.5x (mild increase)
		[95, 100, 1.5]     // Finals Week: 1.5x (mild increase)
	];
	float current_boost <- 1.0;  // the active multiplier for today (reset each tick)

	// ── Experiment controls ───────────────────────────────────
	// These are changed by each experiment to test different scenarios.
	string network_type <- "multiplex";       // which network shape to build
	string seeding_strategy <- "random";      // how to pick the initial 20% adopters
	int nb_initial_adopters <- int(M*0.20);   // 200 students start as adopters on day 0

	// ── RQ1 experiment controls ───────────────────────────────
	string active_layers <- "all";    // which network layers are active ("all", "org_only", "friend_only", "class_only")
	float pct_isolated <- 0.0;       // fraction of students with zero connections (totally alone)
	float pct_no_org   <- 0.0;       // fraction of students not in any organization
	int net_avg_degree  <- 6;        // target connections per student for single-topology networks

	// ── Ad fatigue (RQ2) ──────────────────────────────────────
	// After seeing 10 ads, students start ignoring them (receptivity drops by 50%).
	// Models the real-world effect of ad overexposure / banner blindness.
	int   ad_fatigue_threshold <- 10;
	float fatigue_decay        <- 0.5;

	// ── Disadoption (RQ2) ─────────────────────────────────────
	// If fewer than 25% of your neighbors use GCash, you have a 5% daily chance of quitting.
	// Models: "I tried it but nobody around me uses it, so I stopped."
	float p_disadopt     <- 0.05;
	float peer_support_min <- 0.25;

	// ── Trust vs peer influence (RQ3) ─────────────────────────
	// social_weight controls how much peer pressure matters in the adoption decision.
	// 0.4 means: 40% peer pressure, 30% trust, 30% perceived value.
	// nb_best_friends: how many barkada connections each student gets (0 = disabled).
	float social_weight <- 0.4;
	int   nb_best_friends <- 0;

	// ── Live counters (automatically updated every day) ───────
	// These count how many students are in each state right now.
	// Used for charts, CSV export, and stopping conditions.
	int nb_disadopted <- 0;  // total students who quit during Trial (cumulative across the whole run)
	int nb_unaware  <- 0 update: length(student where (each.state = "Unaware"));
	int nb_aware    <- 0 update: length(student where (each.state = "Aware"));
	int nb_trial    <- 0 update: length(student where (each.state = "Trial"));
	int nb_regular  <- 0 update: length(student where (each.state = "Regular"));
	int nb_advocate <- 0 update: length(student where (each.state = "Advocate"));
	int nb_adopters <- 0 update: nb_trial + nb_regular + nb_advocate;

	// ── Network storage ──────────────────────────────────────
	// These hold the actual connection graphs. Built during init, used every tick.
	// nil = layer is disabled or not yet built.
	graph org_network;
	graph friend_network;
	graph class_network;
	graph best_friend_network;
	float computed_avg_degree <- 6.0;  // average connections per student (calculated after building networks)

	// ═══════════════════════════════════════════════════════════
	//  INITIALIZATION — runs once when the simulation starts
	// ═══════════════════════════════════════════════════════════

	init {
		if (baseline_mode) {
			// BASELINE MODE (Stage A validation):
			// Create one big random network where everyone is roughly equally connected.
			// All agents are identical. This matches the Bass ODE assumption of a "well-mixed" population.
			org_network <- generate_random_graph(
				M, int(M * 10 / 2), false, student, edge_agent
			);
			// All three layers point to the same network (no layer distinction in baseline)
			friend_network <- org_network;
			class_network <- org_network;
			write "Baseline network: " + length(org_network.edges) + " edges";
		} else {
			// FULL MODEL (Stage B/C experiments):
			// Create heterogeneous students and build realistic networks.

			if (empirical_mode) {
				// STAGE C (empirical validation):
				// Load 100 agents from the real-survey cohort + 300 synthetic equal-persona agents.
				// Population is scaled down from 1000 -> 400 to keep the 25/75 split clean.
				M <- nb_empirical + nb_synthetic;

				file cohort_file <- csv_file(empirical_cohort_file, ",", true);
				matrix<string> cohort <- matrix<string>(cohort_file);
				// Column order (see analysis/empirical_cohort.py):
				//   0=source_id, 1=persona, 2=security_belief, 3=social_susceptibility,
				//   4=price_fairness, 5=message_quality, 6=involvement,
				//   7=adoption_threshold, 8=ground_truth_state
				int loaded <- min(nb_empirical, cohort.rows);
				loop r from: 0 to: loaded - 1 {
					string persona_name <- cohort[1, r];
					int p_idx <- persona_name_to_idx contains_key persona_name
						? persona_name_to_idx[persona_name]
						: 3;  // default to Cautious Adopter if unknown
					create student with: [
						is_empirical        :: true,
						source_id           :: int(cohort[0, r]),
						persona             :: p_idx,
						security_belief     :: float(cohort[2, r]),
						social_susceptibility :: float(cohort[3, r]),
						price_fairness      :: float(cohort[4, r]),
						message_quality     :: float(cohort[5, r]),
						involvement         :: float(cohort[6, r]),
						adoption_threshold  :: float(cohort[7, r]),
						ground_truth_state  :: cohort[8, r]
					];
				}
				write "Loaded " + loaded + " empirical agents from cohort CSV.";

				// Synthetic filler: 300 equal-persona agents via the standard init path
				create student number: nb_synthetic;
				write "Created " + nb_synthetic + " synthetic filler agents.";
			} else {
				// STAGE B: 1,000 fully synthetic students (unchanged default)
				create student number: M;
			}

			// === Mark special students ===

			// Isolated students: completely disconnected from everyone.
			// They can only adopt through advertising — nobody can tell them about GCash.
			int nb_isolated <- int(M * pct_isolated);
			if (nb_isolated > 0) {
				ask nb_isolated among student {
					is_isolated <- true;
				}
			}

			// No-org students: not in any organization, but still have friends and classmates.
			// They miss the strong org influence (w=0.8) but get medium/weak ties.
			int nb_no_org <- int(M * pct_no_org);
			if (nb_no_org > 0) {
				ask nb_no_org among (student where (!each.is_isolated)) {
					org_id <- -1;
				}
			}

			// Two filtered lists used throughout network generation:
			// connected = everyone except isolated students
			// org_eligible = connected students who belong to an org
			list<student> connected <- student where (!each.is_isolated);
			list<student> org_eligible <- connected where (each.org_id >= 0);

			if (network_type = "multiplex") {
				// ═════════════════════════════════════════════════
				// MULTIPLEX: 3 separate layers with different structures
				// This is the most realistic model of a campus.
				// ═════════════════════════════════════════════════

				// --- LAYER 1: Organization Network (strong ties) ---
				// Students in the same org are densely connected (60% chance per pair).
				// Between orgs, very few bridges exist (0.2% chance).
				// Think of it as: within YSES everyone knows each other, but YSES↔ACSS has few links.
				org_network <- graph([]);
				ask student { org_network <- org_network add_node self; }
				loop org_idx from: 0 to: nb_orgs - 1 {
					list<student> org_members <- org_eligible where (each.org_id = org_idx);
					loop i from: 0 to: length(org_members) - 2 {
						loop j from: i + 1 to: length(org_members) - 1 {
							if (flip(0.6)) {
								org_network <- org_network add_edge (org_members[i]::org_members[j]);
							}
						}
					}
				}
				// Rare inter-org bridges (someone who knows a person in another org)
				loop i from: 0 to: length(org_eligible) - 2 {
					loop j from: i + 1 to: length(org_eligible) - 1 {
						if (org_eligible[i].org_id != org_eligible[j].org_id and flip(0.002)) {
							org_network <- org_network add_edge (org_eligible[i]::org_eligible[j]);
						}
					}
				}
				write "Org network: " + length(org_network.edges) + " edges";

				// --- LAYER 2: Friend Network (medium ties, small-world) ---
				// Imagine all students in a circle. Each knows 6 neighbors (3 left, 3 right).
				// Then ~100 random "shortcut" friendships are added across the circle.
				// Plus 30% of org connections also appear here (org-mates are often friends).
				// This creates the "small-world" property: tight clusters with some long-range links.
				friend_network <- graph([]);
				list<student> stu_list <- list(connected);
				ask student { friend_network <- friend_network add_node self; }
				int k_half <- 3;  // 3 neighbors on each side = 6 total (ring lattice)
				int n_conn <- length(stu_list);
				loop i from: 0 to: n_conn - 1 {
					loop offset from: 1 to: k_half {
						int j <- mod(i + offset, n_conn);  // mod wraps around: student 999 connects to student 0
						friend_network <- friend_network add_edge (stu_list[i]::stu_list[j]);
					}
				}
				// Random shortcuts (the "small-world" part — like knowing someone in a different friend group)
				int n_shortcuts <- int(n_conn * 0.1);
				loop s_idx from: 0 to: n_shortcuts - 1 {
					student s <- one_of(connected);
					student t <- one_of(connected where (each != s));
					if (!(friend_network contains_edge (s::t))) {
						friend_network <- friend_network add_edge (s::t);
					}
				}
				// Copy some org connections into the friend layer (your org-mate is often your friend too)
				loop e over: org_network.edges {
					if (flip(p_overlap)) {
						student s <- student(org_network source_of e);
						student t <- student(org_network target_of e);
						if (!(friend_network contains_edge (s::t))) {
							friend_network <- friend_network add_edge (s::t);
						}
					}
				}
				write "Friend network: " + length(friend_network.edges) + " edges";

				// --- LAYER 3: Class Network (weak ties, college-based) ---
				// Same college? 5% chance of sharing a class. Different college? 0.5%.
				// Lots of connections but all low-influence.
				class_network <- graph([]);
				ask student { class_network <- class_network add_node self; }
				loop i from: 0 to: length(connected) - 2 {
					loop j from: i + 1 to: length(connected) - 1 {
						float edge_prob <- 0.005;  // different college: 0.5% chance
						if (connected[i].college_id = connected[j].college_id) { edge_prob <- 0.05; }  // same college: 5%
						if (flip(edge_prob)) {
							class_network <- class_network add_edge (connected[i]::connected[j]);
						}
					}
				}
				write "Class network: " + length(class_network.edges) + " edges";

				// --- LAYER REMOVAL (for exp1b_layers) ---
				// Turn off layers we don't want. Setting to nil makes the WOM/BDI code skip them.
				if (active_layers = "org_only") {
					friend_network <- nil;
					class_network <- nil;
				} else if (active_layers = "friend_only") {
					org_network <- nil;
					class_network <- nil;
				} else if (active_layers = "class_only") {
					org_network <- nil;
					friend_network <- nil;
				}

			} else if (network_type = "random") {
				// ═════════════════════════════════════════════════
				// RANDOM NETWORK: everyone has ~6 random connections.
				// No clusters, no structure. Like randomly assigning lab partners.
				// All three layers share the same graph.
				// ═════════════════════════════════════════════════
				org_network <- graph([]);
				ask student { org_network <- org_network add_node self; }
				// edge_prob is set so that average connections per student ≈ 6
				float edge_prob <- float(net_avg_degree) / float(length(connected) - 1);
				loop i from: 0 to: length(connected) - 2 {
					loop j from: i + 1 to: length(connected) - 1 {
						if (flip(edge_prob)) {
							org_network <- org_network add_edge (connected[i]::connected[j]);
						}
					}
				}
				friend_network <- org_network;
				class_network <- org_network;
				write "Random network: " + length(org_network.edges) + " edges";

			} else if (network_type = "small_world") {
				// ═════════════════════════════════════════════════
				// SMALL-WORLD NETWORK: ring of students with random shortcuts.
				// Tight friend groups + occasional cross-campus bridges.
				// "Six degrees of separation."
				// ═════════════════════════════════════════════════
				org_network <- graph([]);
				list<student> stu_list <- list(connected);
				ask student { org_network <- org_network add_node self; }
				int k_half <- int(net_avg_degree / 2);  // 3 neighbors on each side
				int n_conn <- length(stu_list);
				// Build ring: each student connects to k nearest neighbors
				loop i from: 0 to: n_conn - 1 {
					loop offset from: 1 to: k_half {
						int j <- mod(i + offset, n_conn);
						org_network <- org_network add_edge (stu_list[i]::stu_list[j]);
					}
				}
				// Add random shortcuts (10% of population size)
				int n_shortcuts <- int(n_conn * 0.1);
				loop s_idx from: 0 to: n_shortcuts - 1 {
					student s <- one_of(connected);
					student t <- one_of(connected where (each != s));
					if (!(org_network contains_edge (s::t))) {
						org_network <- org_network add_edge (s::t);
					}
				}
				friend_network <- org_network;
				class_network <- org_network;
				write "Small-world network: " + length(org_network.edges) + " edges";

			} else if (network_type = "scale_free") {
				// ═════════════════════════════════════════════════
				// SCALE-FREE NETWORK: a few "popular" students have tons of connections,
				// most students have only a few. Think Instagram followers.
				// Built using Barabási-Albert preferential attachment:
				// new students prefer to connect to already-popular students.
				// ═════════════════════════════════════════════════
				org_network <- graph([]);
				list<student> stu_list <- list(connected);
				int m_ba <- max(1, int(net_avg_degree / 2));  // each new student connects to 3 existing ones
				int n_conn <- length(stu_list);

				// Start with a small fully-connected seed group (4 students all connected)
				loop i from: 0 to: m_ba {
					org_network <- org_network add_node stu_list[i];
				}
				loop i from: 0 to: m_ba - 1 {
					loop j from: i + 1 to: m_ba {
						org_network <- org_network add_edge (stu_list[i]::stu_list[j]);
					}
				}

				// Add remaining 996 students one by one.
				// Each new student picks 3 existing students to connect to.
				// The trick: pick a random EDGE, then pick one of its endpoints.
				// Students with more edges show up as endpoints more often = "rich get richer".
				loop i from: m_ba + 1 to: n_conn - 1 {
					org_network <- org_network add_node stu_list[i];
					list<student> targets <- [];
					int attempts <- 0;
					loop while: length(targets) < m_ba and attempts < m_ba * 50 {
						if (length(org_network.edges) > 0) {
							unknown rand_edge <- one_of(org_network.edges);
							list<student> endpoints <- [
								student(org_network source_of rand_edge),
								student(org_network target_of rand_edge)
							];
							student candidate <- one_of(endpoints);
							if (candidate != stu_list[i] and !(targets contains candidate)) {
								targets <- targets + [candidate];
							}
						}
						attempts <- attempts + 1;
					}
					loop t over: targets {
						org_network <- org_network add_edge (stu_list[i]::t);
					}
				}

				// Isolated students still need to be in the graph (as disconnected dots)
				ask student where (each.is_isolated) {
					if (!(org_network contains_vertex self)) {
						org_network <- org_network add_node self;
					}
				}

				friend_network <- org_network;
				class_network <- org_network;
				write "Scale-free network: " + length(org_network.edges) + " edges";
			}

			// === Build barkada (best-friend) layer if enabled ===
			// Each student picks nb_best_friends random close friends.
			// These connections have w=0.95 (strongest influence), provide a +0.2 social norm boost,
			// and protect against disadoption (if your barkada uses GCash, you won't quit).
			if (nb_best_friends > 0) {
				best_friend_network <- graph([]);
				ask student { best_friend_network <- best_friend_network add_node self; }
				ask connected {
					list<student> candidates <- connected where (each != self);
					int nb_to_pick <- min(nb_best_friends, length(candidates));
					list<student> picks <- nb_to_pick among candidates;
					loop bf over: picks {
						if (!(best_friend_network contains_edge (self::bf))) {
							best_friend_network <- best_friend_network add_edge (self::bf);
						}
					}
				}
				write "Best-friend network: " + length(best_friend_network.edges) + " edges";
			}

			// === Calculate average connections per student ===
			// Used later to normalize WOM influence so denser networks aren't unfairly stronger.
			// Only counts edges from active layers (skips nil layers and avoids double-counting shared graphs).
			int total_edges <- 0;
			if (org_network != nil) { total_edges <- total_edges + length(org_network.edges); }
			if (friend_network != nil and friend_network != org_network) {
				total_edges <- total_edges + length(friend_network.edges);
			}
			if (class_network != nil and class_network != org_network) {
				total_edges <- total_edges + length(class_network.edges);
			}
			if (best_friend_network != nil) {
				total_edges <- total_edges + length(best_friend_network.edges);
			}
			computed_avg_degree <- max(1.0, float(total_edges * 2) / float(M));
			write "Computed avg degree: " + computed_avg_degree;
		}

		// === Pick the first 200 students to start as adopters ===
		// These represent students who already used GCash before the semester started.
		if (!baseline_mode) {
			if (seeding_strategy = "opinion_leader") {
				// Pick the most connected students (the "influencers")
				list<student> sorted_by_degree;
				if (org_network != nil) {
					sorted_by_degree <- student sort_by (-(org_network degree_of each));
				} else if (friend_network != nil) {
					sorted_by_degree <- student sort_by (-(friend_network degree_of each));
				} else if (class_network != nil) {
					sorted_by_degree <- student sort_by (-(class_network degree_of each));
				} else {
					sorted_by_degree <- list(student);
				}
				loop i from: 0 to: nb_initial_adopters - 1 {
					ask sorted_by_degree[i] { state <- "Trial"; }
				}
			} else {
				// Pick 200 random students
				ask nb_initial_adopters among student { state <- "Trial"; }
			}
		}

		write "Created " + M + " agents. Baseline: " + baseline_mode;
	}

	// ═══════════════════════════════════════════════════════════
	//  DAILY PROCESSES — these run in order every simulated day
	// ═══════════════════════════════════════════════════════════

	// --- STEP 0: Check if a campus event is happening today ---
	// If yes, boost the advertising probability for today.
	reflex update_event_boost {
		current_boost <- 1.0;
		if (!baseline_mode) {
			loop idx from: 0 to: length(campus_events) - 1 {
				list ev <- campus_events[idx];
				int start_day <- int(ev[0]);
				int end_day <- int(ev[1]);
				float boost <- float(ev[2]);
				if (cycle >= start_day and cycle <= end_day) {
					current_boost <- max(current_boost, boost);
				}
			}
		}
	}

	// --- STEP 1: Advertising hits students ---
	// Every Unaware/Aware student has a small daily chance of seeing an ad.
	// If they see it: Unaware students may become Aware, and ad exposure is tracked for fatigue.
	reflex advertising {
		ask student where (each.state = "Unaware" or each.state = "Aware") {
			if (flip(p_ad * current_boost)) {
				// Count this ad hit (builds toward fatigue)
				ad_exposure <- ad_exposure + 1;
				if (!baseline_mode and ad_exposure >= ad_fatigue_threshold) {
					ad_fatigued <- true;  // "I'm sick of these ads"
				}

				// Only Unaware students can change state from an ad
				if (state = "Unaware") {
					if (baseline_mode) {
						// Baseline: ad directly creates adopter (simple Bass model)
						state <- "Trial";
						days_in_state <- 0;
					} else {
						// Full model: ad must pass through message_quality filter
						// Fatigued students are half as receptive
						float effective_mq <- message_quality;
						if (ad_fatigued) {
							effective_mq <- message_quality * fatigue_decay;
						}
						if (flip(effective_mq)) {
							state <- "Aware";  // heard about it, but hasn't tried yet
						}
					}
				}
			}
		}
	}

	// --- STEP 2: Word-of-Mouth (adopters try to influence neighbors) ---
	// Every student who uses GCash (Trial/Regular/Advocate) talks to their connections.
	// Each connection has a chance of being influenced, based on tie weight and credibility.
	reflex word_of_mouth {
		// Get all current adopters
		list<student> adopters <- student where (
			each.state = "Trial" or each.state = "Regular" or each.state = "Advocate"
		);

		ask adopters {
			// Advocates are 1.5x more convincing than regular users
			float credibility <- 1.0;
			if (state = "Advocate") { credibility <- c_advocate; }

			// Build a map: neighbor → strongest tie weight across all layers.
			// If someone is both your org-mate (0.8) and best friend (0.95), they get 0.95.
			map neighbor_weights <- [];

			// Check org layer neighbors
			if (org_network != nil) {
				loop n over: list<student>(org_network neighbors_of self) {
					if (n != nil and (n.state = "Unaware" or n.state = "Aware")) {
						float current <- (neighbor_weights contains_key n) ? float(neighbor_weights[n]) : 0.0;
						neighbor_weights[n] <- max(current, w_org);
					}
				}
			}
			// Check friend layer (skip if same graph as org — avoids double counting)
			if (!baseline_mode and friend_network != nil and friend_network != org_network) {
				loop n over: list<student>(friend_network neighbors_of self) {
					if (n != nil and (n.state = "Unaware" or n.state = "Aware")) {
						float current <- (neighbor_weights contains_key n) ? float(neighbor_weights[n]) : 0.0;
						neighbor_weights[n] <- max(current, w_friend);
					}
				}
			}
			// Check class layer
			if (!baseline_mode and class_network != nil and class_network != org_network) {
				loop n over: list<student>(class_network neighbors_of self) {
					if (n != nil and (n.state = "Unaware" or n.state = "Aware")) {
						float current <- (neighbor_weights contains_key n) ? float(neighbor_weights[n]) : 0.0;
						neighbor_weights[n] <- max(current, w_class);
					}
				}
			}
			// Check best-friend layer
			if (!baseline_mode and best_friend_network != nil) {
				loop n over: list<student>(best_friend_network neighbors_of self) {
					if (n != nil and (n.state = "Unaware" or n.state = "Aware")) {
						float current <- (neighbor_weights contains_key n) ? float(neighbor_weights[n]) : 0.0;
						neighbor_weights[n] <- max(current, w_best);
					}
				}
			}

			// Now try to influence each unique non-adopter neighbor
			loop k over: neighbor_weights.keys {
				if (k != nil) {
					student neighbor <- student(k);
					if (neighbor != nil) {
						float tie_weight <- float(neighbor_weights[k]);
						// Influence formula: (base WOM / avg connections) × credibility × tie strength
						// Dividing by avg_degree ensures denser networks don't get unfairly more total influence
						float per_edge_prob <- p_wom / computed_avg_degree;
						float influence <- per_edge_prob * credibility * tie_weight;

						if (flip(influence)) {
							if (baseline_mode) {
								// Baseline: WOM directly converts (simple Bass)
								if (neighbor.state = "Unaware") {
									neighbor.state <- "Trial";
									neighbor.days_in_state <- 0;
									influence_spread_count <- influence_spread_count + 1;
								}
							} else {
								// Full model: Unaware → Aware (just heard about it)
								// Already Aware → accumulate social pressure (BDI decides later)
								if (neighbor.state = "Unaware") {
									neighbor.state <- "Aware";
								} else if (neighbor.state = "Aware") {
									neighbor.social_pressure <- neighbor.social_pressure + influence;
									influence_spread_count <- influence_spread_count + 1;
								}
							}
						}
					}
				}
			}
		}
	}

	// --- STEP 2b: BDI Adoption Decision (full model only) ---
	// Every Aware student asks themselves: "Should I try GCash?"
	// They look at: (1) do I trust it? (2) do my friends use it? (3) is it worth it?
	// If their combined belief score exceeds the threshold, they adopt.
	reflex bdi_deliberation when: !baseline_mode {
		ask student where (each.state = "Aware") {
			// Count what fraction of my neighbors are adopters (across all layers)
			list<student> all_neighbors <- [];
			if (org_network != nil) {
				all_neighbors <- all_neighbors + list<student>(org_network neighbors_of self);
			}
			if (friend_network != nil and friend_network != org_network) {
				all_neighbors <- all_neighbors + list<student>(friend_network neighbors_of self);
			}
			if (class_network != nil and class_network != org_network) {
				all_neighbors <- all_neighbors + list<student>(class_network neighbors_of self);
			}
			if (best_friend_network != nil) {
				all_neighbors <- all_neighbors + list<student>(best_friend_network neighbors_of self);
			}
			all_neighbors <- remove_duplicates(all_neighbors);

			int total_neighbors <- length(all_neighbors);
			int adopter_neighbors <- length(all_neighbors where (
				each.state = "Trial" or each.state = "Regular" or each.state = "Advocate"
			));

			// Check if any best friend uses GCash (barkada effect)
			bool best_friend_adopted <- false;
			if (best_friend_network != nil) {
				list<student> bfs <- list<student>(best_friend_network neighbors_of self);
				best_friend_adopted <- length(bfs where (
					each.state = "Trial" or each.state = "Regular" or each.state = "Advocate"
				)) > 0;
			}

			// Calculate social norm: what fraction of my network uses GCash?
			if (total_neighbors > 0) {
				belief_social_norm <- float(adopter_neighbors) / float(total_neighbors);
				// Barkada boost: if your best friend uses it, it feels like more people use it (+0.2)
				if (best_friend_adopted) {
					belief_social_norm <- min(1.0, belief_social_norm + 0.2);
				}
			} else {
				belief_social_norm <- 0.0;  // isolated student: no social pressure
			}

			// DESIRE CHECK 1: Is the platform too risky?
			// If trust is below 0.3, refuse no matter what. Hard stop.
			bool desire_avoid_risk <- security_belief < r_threshold;

			// DESIRE CHECK 2: Is there enough social proof for my personality?
			// Social Followers need very little proof (susceptibility=0.9).
			// Disengaged students need a lot (susceptibility=0.3).
			bool desire_adopt <- belief_social_norm >= adoption_threshold * (1.0 - social_susceptibility);

			// FINAL DECISION: If both desire checks pass, compute the belief score.
			// belief = 30% trust + 30% value + 40% peer pressure
			// If this exceeds the threshold (default 0.35), adopt.
			if (!desire_avoid_risk and desire_adopt) {
				float other_weight <- (1.0 - social_weight) / 2.0;
				float weighted_belief <- other_weight * security_belief
					+ other_weight * belief_value
					+ social_weight * belief_social_norm;

				if (weighted_belief > b_threshold) {
					state <- "Trial";
					days_in_state <- 0;
				}
			}
		}
	}

	// --- STEP 2c: Disadoption (full model only) ---
	// Trial users check: "Am I alone in using this?"
	// If fewer than 25% of neighbors use GCash AND no best friend uses it → 5% daily chance of quitting.
	reflex disadoption when: !baseline_mode {
		ask student where (each.state = "Trial") {
			// Same neighbor counting as BDI — what fraction of people around me are adopters?
			list<student> all_neighbors <- [];
			if (org_network != nil) {
				all_neighbors <- all_neighbors + list<student>(org_network neighbors_of self);
			}
			if (friend_network != nil and friend_network != org_network) {
				all_neighbors <- all_neighbors + list<student>(friend_network neighbors_of self);
			}
			if (class_network != nil and class_network != org_network) {
				all_neighbors <- all_neighbors + list<student>(class_network neighbors_of self);
			}
			if (best_friend_network != nil) {
				all_neighbors <- all_neighbors + list<student>(best_friend_network neighbors_of self);
			}
			all_neighbors <- remove_duplicates(all_neighbors);

			float peer_support <- 0.0;
			if (length(all_neighbors) > 0) {
				int adopter_neighbors <- length(all_neighbors where (
					each.state = "Trial" or each.state = "Regular" or each.state = "Advocate"
				));
				peer_support <- float(adopter_neighbors) / float(length(all_neighbors));
			}

			// Barkada protection: if any best friend uses GCash, you won't quit
			bool bf_support <- false;
			if (best_friend_network != nil) {
				list<student> bfs <- list<student>(best_friend_network neighbors_of self);
				bf_support <- length(bfs where (
					each.state = "Trial" or each.state = "Regular" or each.state = "Advocate"
				)) > 0;
			}

			// Three conditions must ALL be true to quit:
			// 1. No best friend uses it
			// 2. Less than 25% of neighbors use it
			// 3. Random 5% daily chance (even lonely users might stick around)
			if (!bf_support and peer_support < peer_support_min and flip(p_disadopt)) {
				state <- "Aware";         // back to "I know about it but I stopped using it"
				days_in_state <- 0;
				nb_disadopted <- nb_disadopted + 1;
			}
		}
	}

	// --- STEP 3: Promotions (Trial → Regular → Advocate) ---
	reflex state_progression {
		// Used GCash for 7+ days without quitting? You're now a Regular user.
		ask student where (each.state = "Trial" and each.days_in_state >= t_trial) {
			state <- "Regular";
			days_in_state <- 0;
		}

		// Convinced 3+ people? You're now an Advocate (1.5x influence multiplier).
		ask student where (each.state = "Regular" and each.influence_spread_count >= n_advocate) {
			state <- "Advocate";
			days_in_state <- 0;
		}
	}

	// --- STEP 4: End of day bookkeeping ---
	reflex update_state {
		ask student {
			days_in_state <- days_in_state + 1;
			social_pressure <- 0.0;  // reset for tomorrow (accumulates fresh from WOM)
		}
	}

	// --- STEP 5: Save data to CSV ---
	// Baseline mode: simple 3-column CSV for validation
	reflex save_data when: baseline_mode {
		save [int(self), cycle, nb_adopters]
			to: "../output/baseline_all_runs.csv"
			format: "csv"
			rewrite: (cycle = 0 and int(self) = 0)
			header: false;
	}

	// Stage C: empirical validation — each simulation writes its own CSV.
	// Two-phase save: cycle=0 creates the file with a header; cycle=T appends one row per empirical agent.
	// Analysis script analysis/empirical_validation.py aggregates across runs.

	reflex save_empirical_header when: empirical_mode and is_batch and cycle = 0 {
		int run_id <- int(self);
		save ["run_id", "source_id", "persona", "final_state", "ground_truth_state"]
			to: "../output/empirical_validation_" + run_id + ".csv"
			format: "csv"
			rewrite: true
			header: false;
	}

	reflex save_empirical_rows when: empirical_mode and is_batch and cycle = T {
		int run_id <- int(self);
		ask student where (each.is_empirical) {
			save [run_id, source_id, persona, state, ground_truth_state]
				to: "../output/empirical_validation_" + run_id + ".csv"
				format: "csv"
				rewrite: false
				header: false;
		}
	}

	// Experiment mode: 5-column CSV with experiment parameter value
	// Filename includes the experiment name and parameter, e.g. "exp1_topology_random.csv"
	reflex save_experiment_data when: !baseline_mode and is_batch and experiment_id != "" {
		string param_val <- "";
		if (experiment_id = "exp1_topology") { param_val <- network_type; }
		else if (experiment_id = "exp1b_layers") { param_val <- active_layers; }
		else if (experiment_id = "exp2_advertising") { param_val <- string(p_ad); }
		else if (experiment_id = "exp3_trust") { param_val <- string(b_threshold); }
		else if (experiment_id = "exp3c_best_friends") { param_val <- string(nb_best_friends); }

		save [int(self), cycle, nb_adopters, nb_disadopted, param_val]
			to: "../output/" + experiment_id + "_" + param_val + ".csv"
			format: "csv"
			rewrite: (cycle = 0 and int(self) = 0)
			header: true;
	}

	// --- Stop the simulation after one semester (GUI mode only) ---
	reflex stop when: cycle >= T and !is_batch {
		do pause;
	}

}


// ═══════════════════════════════════════════════════════════════════
//  STUDENT AGENT — each of the 1,000 students is one of these
// ═══════════════════════════════════════════════════════════════════

species student {

	// --- Current adoption state ---
	string state                <- "Unaware";  // starts as Unaware (never heard of GCash)
	int    days_in_state        <- 0;          // how many days in current state
	int    influence_spread_count <- 0;        // how many people I've convinced (needed for Advocate promotion)
	float  social_pressure      <- 0.0;        // accumulated WOM pressure today (resets daily)
	int    ad_exposure          <- 0;          // how many ads I've seen total (for fatigue)
	bool   ad_fatigued          <- false;      // true = I'm ignoring ads now

	// --- Personality (set from persona profile during init) ---
	int   persona              <- 0;     // which of the 5 types (1-5, or 0 for baseline)
	float security_belief      <- 0.5;   // how much I trust GCash (0=don't trust, 1=fully trust)
	float social_susceptibility <- 0.5;  // how easily influenced by peers (0=independent, 1=follower)
	float price_fairness       <- 0.5;   // do I think the fees are fair? (0=unfair, 1=very fair)
	float message_quality      <- 0.5;   // how receptive am I to ads? (0=ignore, 1=believe everything)
	float involvement          <- 0.5;   // how engaged am I with fintech? (0=don't care, 1=passionate)
	float adoption_threshold   <- 0.3;   // my personal bar for "enough social proof"

	// --- Which org and college I belong to ---
	int org_id     <- 0;      // 0-19 (which of 20 orgs), or -1 if no org
	int college_id <- 0;      // 1-7 (which of 7 colleges)
	bool is_isolated <- false; // true = completely disconnected from everyone

	// --- Empirical-validation tags (Stage C) ---
	// is_empirical: this agent's parameters came from a real survey respondent
	// source_id: the respondent's row index in survey_responses.csv
	// ground_truth_state: the adoption state we want the model to reproduce
	bool   is_empirical       <- false;
	int    source_id          <- -1;
	string ground_truth_state <- "";

	// --- Computed values (updated during BDI deliberation) ---
	float belief_value       <- 0.0;   // 50% price fairness + 50% message quality
	float belief_social_norm <- 0.0;   // fraction of my neighbors who use GCash

	// --- When this student is created ---
	init {
		// Randomly assign to an org and college
		org_id <- rnd(nb_orgs - 1);
		college_id <- rnd(nb_colleges - 1) + 1;

		if (is_empirical) {
			// STAGE C: persona attributes already set via `create ... with:` from the
			// empirical cohort CSV. Just compute the derived belief_value.
			belief_value <- 0.5 * price_fairness + 0.5 * message_quality;
		} else if (!baseline_mode) {
			// FULL MODEL: assign one of 5 personality types randomly (20% each)
			float rand <- rnd(1.0);
			float cumulative <- 0.0;
			loop i from: 0 to: length(persona_proportions) - 1 {
				cumulative <- cumulative + persona_proportions[i];
				if (rand <= cumulative) {
					persona <- i + 1;
					break;
				}
			}
			if (persona = 0) { persona <- length(persona_proportions); }  // safety catch

			// Load personality values from the persona profile table
			list<float> profile <- persona_profiles[persona - 1];
			security_belief <- profile[0];
			social_susceptibility <- profile[1];
			price_fairness <- profile[2];
			message_quality <- profile[3];
			involvement <- profile[4];
			adoption_threshold <- profile[5];
			belief_value <- 0.5 * price_fairness + 0.5 * message_quality;
		} else {
			// BASELINE: all agents are identical (homogeneous population for Bass validation)
			persona <- 0;
			security_belief <- 0.5;
			social_susceptibility <- 0.5;
			price_fairness <- 0.5;
			message_quality <- 0.5;
			involvement <- 0.5;
			adoption_threshold <- 0.0;  // any exposure is enough to adopt
			belief_value <- 0.5;
		}
	}

	// --- Color in the GUI (changes based on adoption state) ---
	rgb color <- #gray;

	reflex update_color {
		switch state {
			match "Unaware"  { color <- #gray;   }  // hasn't heard of GCash
			match "Aware"    { color <- #yellow;  }  // knows about it but hasn't tried
			match "Trial"    { color <- #orange;  }  // trying it out
			match "Regular"  { color <- #blue;    }  // committed user
			match "Advocate" { color <- #green;   }  // actively promoting it
		}
	}

	// --- How to draw this student on the map ---
	aspect default {
		draw circle(2) color: color;
	}

}


// ═══════════════════════════════════════════════════════════════════
//  EDGE AGENT — the lines connecting students in the GUI
// ═══════════════════════════════════════════════════════════════════

species edge_agent {

	aspect default {
		draw shape color: #lightgray;
	}

}


// ═══════════════════════════════════════════════════════════════════
//  EXPERIMENTS — each one tests a different scenario
// ═══════════════════════════════════════════════════════════════════

// --- GUI: Baseline validation (manual, one run at a time) ---
// Use this to visually watch the simulation and check if it looks right.
experiment baseline type: gui {

	parameter "Population size"  var: M;
	parameter "Simulation days"  var: T;
	parameter "Baseline mode"    var: baseline_mode;

	output {
		display "Campus View" type: java2D {
			species edge_agent aspect: default;
			species student aspect: default;
		}
		display "Charts" type: java2D {
			chart "Adoption over time" type: series size: {1.0, 0.5} position: {0.0, 0.0} {
				data "Unaware"  value: nb_unaware  color: #gray;
				data "Aware"    value: nb_aware    color: #yellow;
				data "Trial"    value: nb_trial    color: #orange;
				data "Regular"  value: nb_regular  color: #blue;
				data "Advocate" value: nb_advocate color: #green;
			}
			chart "Cumulative adopters" type: series size: {1.0, 0.5} position: {0.0, 0.5} {
				data "Adopters" value: nb_adopters color: #red;
			}
		}
	}

}


// --- BATCH: 30 runs for Bass ODE validation ---
// Runs the baseline 30 times with different random seeds.
// Output goes to baseline_all_runs.csv for comparison with the Bass ODE.
experiment baseline_batch type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- true;
	parameter "Population" var: M <- 1000;
	parameter "Batch mode" var: is_batch <- true;

	method exploration;
}


// --- GUI: Full model with all features (manual exploration) ---
// Use this to play with parameters and watch the full model in action.
experiment full_model type: gui {

	parameter "Population size"    var: M;
	parameter "Simulation days"    var: T;
	parameter "Baseline mode"      var: baseline_mode <- false;
	parameter "p_ad (advertising)" var: p_ad min: 0.0 max: 0.05 step: 0.001;
	parameter "p_wom (word-of-mouth)" var: p_wom min: 0.0 max: 0.2 step: 0.01;
	parameter "Network overlap"    var: p_overlap min: 0.0 max: 1.0 step: 0.1;
	parameter "Belief threshold"   var: b_threshold min: 0.0 max: 1.0 step: 0.1;
	parameter "Seeding strategy"   var: seeding_strategy;

	output {
		display "Campus View" type: java2D {
			species edge_agent aspect: default;
			species student aspect: default;
		}
		display "Charts" type: java2D {
			chart "Adoption over time" type: series size: {1.0, 0.5} position: {0.0, 0.0} {
				data "Unaware"  value: nb_unaware  color: #gray;
				data "Aware"    value: nb_aware    color: #yellow;
				data "Trial"    value: nb_trial    color: #orange;
				data "Regular"  value: nb_regular  color: #blue;
				data "Advocate" value: nb_advocate color: #green;
			}
			chart "Cumulative adopters" type: series size: {1.0, 0.5} position: {0.0, 0.5} {
				data "Adopters" value: nb_adopters color: #red;
			}
		}
	}
}


// ═══════════════════════════════════════════════════════════════════
//  BATCH EXPERIMENTS (30 runs each, automated)
//  Each one tests a different variable while holding everything else constant.
// ═══════════════════════════════════════════════════════════════════

// --- EXPERIMENT 1: Network Topology (RQ1) ---
// Question: Does the shape of the network matter?
// Tests: random, small-world, scale-free, and multiplex (campus) networks.
experiment exp1_topology type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- false;
	parameter "Batch mode" var: is_batch <- true;
	parameter "Experiment" var: experiment_id <- "exp1_topology";
	parameter "Network type" var: network_type among: ["random", "small_world", "scale_free", "multiplex"];

	method exploration;
}


// --- EXPERIMENT 2: Advertising Intensity (RQ2) ---
// Question: How much advertising is too much?
// Tests: light (0.001), default (0.003), heavy (0.005), aggressive (0.01).
// Ad fatigue and disadoption are always active.
experiment exp2_advertising type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- false;
	parameter "Batch mode" var: is_batch <- true;
	parameter "Experiment" var: experiment_id <- "exp2_advertising";
	parameter "p_ad" var: p_ad among: [0.001, 0.003, 0.005, 0.01];

	method exploration;
}


// --- EXPERIMENT 3: Trust Threshold (RQ3) ---
// Question: At what trust level does adoption collapse?
// Tests: easy (0.1), moderate (0.3), default (0.35), skeptical (0.5), very skeptical (0.7).
experiment exp3_trust type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- false;
	parameter "Batch mode" var: is_batch <- true;
	parameter "Experiment" var: experiment_id <- "exp3_trust";
	parameter "Belief threshold" var: b_threshold among: [0.1, 0.3, 0.35, 0.5, 0.7];

	method exploration;
}


// --- EXPERIMENT 1b: Layer Removal (RQ1) ---
// Question: Which type of connection matters most?
// Tests: all layers, org-only (strong), friend-only (medium), class-only (weak).
experiment exp1b_layers type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- false;
	parameter "Batch mode" var: is_batch <- true;
	parameter "Experiment" var: experiment_id <- "exp1b_layers";
	parameter "Network type" var: network_type <- "multiplex";
	parameter "Active layers" var: active_layers among: ["all", "org_only", "friend_only", "class_only"];

	method exploration;
}


// --- EXPERIMENT 3c: Best Friends / Barkada Effect (RQ3) ---
// Question: Can your barkada keep you from quitting?
// Tests: 0 best friends (no barkada), 1, 3, and 5 best friends per student.
experiment exp3c_best_friends type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- false;
	parameter "Batch mode" var: is_batch <- true;
	parameter "Experiment" var: experiment_id <- "exp3c_best_friends";
	parameter "Best friends per student" var: nb_best_friends among: [0, 1, 3, 5];

	method exploration;
}


// --- STAGE C: Empirical validation ---
// Question: do the 100 agents derived from real survey respondents end up in the
// adoption state their survey answer said they're in?
// Cohort: 100 real-derived agents (from data/empirical_cohort.csv) + 300 synthetic
// filler agents (equal-persona), M=400 total. Full multiplex network, disadoption
// and ad-fatigue active. 30 replications; each writes its own CSV snapshot of
// empirical-agent final states. Aggregated and scored by analysis/empirical_validation.py.
experiment exp_empirical_validation type: batch repeat: 30 keep_seed: false until: (cycle >= 105) {

	parameter "Baseline mode" var: baseline_mode <- false;
	parameter "Batch mode" var: is_batch <- true;
	parameter "Empirical mode" var: empirical_mode <- true;
	parameter "Experiment" var: experiment_id <- "empirical_validation";

	method exploration;
}

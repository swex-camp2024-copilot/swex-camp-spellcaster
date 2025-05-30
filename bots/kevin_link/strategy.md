# Kevin Link Bot Strategy: Tactical Combat System

## Core Principles & State Tracking

Kevin Link is a tactical wizard bot that employs sophisticated state tracking and decision-making to outmaneuver opponents. The bot maintains:

- **Dynamic State Tracking**: Monitors own/opponent HP, mana, cooldowns, positions, shield status, active minions, and artifacts
- **Movement Pattern Analysis**: Tracks both opponent and self-movement patterns for better prediction and positioning
- **Game Phase Awareness**: Implements distinct strategies for early game (turns 1-10) and late game (11+)

## Decision Priority Hierarchy

The bot follows a strict decision priority system:

1. **First-Turn Shield**: Always attempts to shield on first turn
   - Provides early protection against aggressive opponents
   - Enables safer positioning in early game

2. **Early Artifact Racing** (Turns 1-3)
   - Teleports or blinks to high-value health or mana artifacts if HP ≤ 60 or mana ≤ 40
   - Avoids cooldown artifacts when not needed
   - Prioritizes mana artifacts when mana < 60 and health artifacts when HP < 60 during early race

3. **Emergency Response** (`_emergency_response`)
   - Shield if HP ≤ 60 and not already shielded
   - Emergency heal when HP ≤ 30
   - Emergency blink when opponent distance ≤ 3
   - Emergency teleport to nearest health artifact when HP ≤ 35 (correctly references available artifacts)

4. **Offensive Opportunity** (`_offensive_opportunity`)
   - Fireball when opponent is in range (≤ 5) and not shielded
   - Melee attack when adjacent to opponent
   - Aggressive blink to close distance when healthy

5. **Resource Acquisition** (`_resource_strategy`)
   - Trigger when HP ≤ 50 or mana ≤ 40
   - Teleport to critical health or mana artifacts; avoid teleporting to cooldown artifacts unless no other options
   - Blink toward resource artifacts when distance > 1
   - Move toward weighted best artifact with lower preference for cooldown artifacts to conserve mana

6. **Minion Management**
   - Summon first minion by turn 2
   - Position minions at least 2 squares away diagonally, avoiding board edges (1-8 range)
   - Maintain safe distance between wizard and minions to prevent collisions
   - Favor positions that maximize distance from opponent

7. **Positional Advantage** (`_positional_advantage`)
   - Proactive shielding when opponent is within range (≤ 5), but only 10% likelihood to conserve mana
   - Healing when moderately damaged and not under immediate threat
   - Blink to maintain optimal combat distance

8. **Movement Strategy** (`_calculate_move`)
   - Prioritize artifact collection when resources are low
   - Defensive retreat when low health
   - Maintain optimal distance based on situation
   - Intelligent strafing to avoid predictable movement patterns

## Helper Strategies & Algorithms

- **`_calculate_optimal_distance`**: Dynamically determines ideal spacing
  - 7 units when at very low health
  - 6 units when low health without shield
  - 5 units when fireball ready and opponent not shielded
  - 3 units when shielded and healthy
  - 5 units as default

- **`_safe_retreat_direction`**: Enhanced evasion calculation
  - Higher weights for distance from primary threat (4x) and secondary threats (1.5x)
  - Precisely calculates perpendicularity using vector math and dot products
  - Strong penalty for moving directly toward threats (-10)
  - Significant bonus for perpendicular movement (+5)
  - Heavily penalizes board edges (-10) and corners (-20)
  - Prefers diagonal movement for faster escape (+2)
  - Includes randomization to reduce predictability
  - Penalizes repeating previous movement patterns

- **`_intelligent_strafe`**: Improved lateral movement system
  - Prefers perpendicular movement to main axis of distance
  - Stronger penalties for moving near board edges (-30) and corners (-50)
  - Higher penalty for moving near own minions (-50) to avoid collisions
  - Considers proximity to valuable artifacts
  - Includes diagonal movements in fallback options
  - Uses increased randomization to avoid predictable patterns

- **`_direction_toward`**: Optimized for blink ability
  - Special handling for blink distance (typically 2 spaces)
  - Maximizes blink range using Manhattan distance calculation
  - Ensures moves stay within blink's 4-cell range limit
  - Improved boundary adjustment logic
  - Dynamic direction calculation based on target position

- **`_predict_position`**: Anticipates opponent movement
  - Analyzes consistent movement patterns
  - Predicts likely next position for targeting
  - Ensures predictions stay within board boundaries

- **`_choose_best_artifact`**: Sophisticated artifact evaluation
  - Scores artifacts based on current needs (health/mana)
  - Considers distance and risk of collection
  - Evaluates whether opponent might reach artifact first
  - Adjusts value based on game phase

- **`_calculate_move_toward_artifact`**: Improved resource targeting
  - Properly factors in current HP and mana for better prioritization
  - Falls back to conservative estimation when health/mana unknown
  - Integrates with general movement system for consistent behavior

By combining these strategic elements, Kevin Link employs consistent tactical decision-making with enhanced positional awareness, making it a formidable and unpredictable wizard in the arena.

## Decision Flow Visualization

The following flowchart illustrates the complete decision-making process of the Kevin Link bot:

```mermaid
flowchart TD
    A[Start Turn] --> B[Update State Tracking]
    B --> C[Track Enemy Positions & Patterns]
    C --> D[Update Game Phase & Attack Detection]
    D --> E{First Round?}
    
    E -->|Yes| F[Cast Shield if Available]
    E -->|No| G{Early Game & Critical Resources?}
    
    G -->|Yes, HP ≤ 60 OR Mana ≤ 60| H[Early Artifact Racing]
    H --> I{Artifact Distance > 2?}
    I -->|Yes| J[Teleport to Best Artifact]
    I -->|No| K{Distance > 1?}
    K -->|Yes| L[Blink Toward Artifact]
    K -->|No| M[Continue to Priority System]
    
    G -->|No| M
    F --> M
    J --> END[Execute Action]
    L --> END
    
    M --> N[Priority 1: Emergency Response]
    N --> O{HP ≤ 60 & Not Shielded?}
    O -->|Yes| P[Cast Shield]
    O -->|No| Q{HP ≤ 30?}
    Q -->|Yes| R[Emergency Heal]
    Q -->|No| S{Under Heavy Attack?}
    S -->|Yes| T{Distance ≤ 3?}
    T -->|Yes| U[Emergency Blink Away]
    T -->|No| V{HP ≤ 35?}
    V -->|Yes| W[Teleport to Health Artifact]
    V -->|No| X[Priority 2: Offensive Opportunity]
    S -->|No| X
    
    X --> Y{HP > Opponent + 20?}
    Y -->|Yes| Z{Opponent Shielded?}
    Z -->|No| AA{Distance ≤ 5?}
    AA -->|Yes| BB[Fireball with Prediction]
    AA -->|No| CC{Adjacent?}
    CC -->|Yes| DD[Melee Attack]
    CC -->|No| EE[Aggressive Blink]
    Z -->|Yes| FF[Priority 3: Resource Strategy]
    Y -->|No| FF
    
    FF --> GG{HP ≤ 50 OR Mana ≤ 40?}
    GG -->|Yes| HH[Find Best Artifact]
    HH --> II{Critical Need & Better Options?}
    II -->|Yes| JJ[Avoid Cooldown Artifacts]
    II -->|No| KK[Consider All Artifacts]
    JJ --> LL{Distance ≥ 5 OR Critical?}
    KK --> LL
    LL -->|Yes| MM[Teleport to Artifact]
    LL -->|No| NN{Distance > 1?}
    NN -->|Yes| OO[Blink Toward Artifact]
    NN -->|No| PP[Move Toward Artifact]
    GG -->|No| QQ[Priority 4: Minion Management]
    
    QQ --> RR{Turn ≤ 2 & No Minions?}
    RR -->|Yes| SS[Summon Defensive Minion]
    SS --> TT[Position 2+ Squares Away]
    TT --> UU[Avoid Board Edges 1-8]
    RR -->|No| VV{Need More Minions?}
    VV -->|Yes| WW[Strategic Summon Position]
    VV -->|No| XX[Priority 5: Positional Advantage]
    
    XX --> YY{Distance ≤ 4 & Not Shielded?}
    YY -->|Yes| ZZ{HP ≤ 70?}
    ZZ -->|Yes| AAA[Cast Shield]
    ZZ -->|No| BBB{Distance ≤ 5 & Mana ≥ 40?}
    BBB -->|Yes| CCC{Random 10%?}
    CCC -->|Yes| DDD[Proactive Shield]
    CCC -->|No| EEE[Priority 6: Movement]
    YY -->|No| FFF{HP ≤ 75 & Distance ≥ 4?}
    FFF -->|Yes| GGG[Heal]
    FFF -->|No| HHH{Need Distance Adjustment?}
    HHH -->|Yes| III[Blink to Optimal Distance]
    HHH -->|No| EEE
    BBB -->|No| EEE
    
    EEE --> JJJ{Need Artifacts?}
    JJJ -->|Yes, HP ≤ 70 OR Mana ≤ 60| KKK[Move Toward Best Artifact]
    JJJ -->|No| LLL{Low HP & Close?}
    LLL -->|Yes, HP ≤ 40 & Distance ≤ 3| MMM[Safe Retreat]
    LLL -->|No| NNN{At Optimal Distance?}
    NNN -->|No| OOO{Too Close?}
    OOO -->|Yes| PPP[Move Away]
    OOO -->|No| QQQ[Move Closer]
    NNN -->|Yes| RRR[Intelligent Strafe]
    
    %% All decision paths lead to action execution
    P --> END
    R --> END
    U --> END
    W --> END
    BB --> END
    DD --> END
    EE --> END
    MM --> END
    OO --> END
    PP --> END
    UU --> END
    WW --> END
    AAA --> END
    DDD --> END
    GGG --> END
    III --> END
    KKK --> END
    MMM --> END
    PPP --> END
    QQQ --> END
    RRR --> END
    
    END --> SSS[Return Move + Spell Action]
    
    %% Styling for different priority levels
    classDef emergency fill:#ff6b6b,stroke:#d63031,color:#fff
    classDef offensive fill:#fd79a8,stroke:#e84393,color:#fff
    classDef resource fill:#fdcb6e,stroke:#e17055,color:#000
    classDef minion fill:#6c5ce7,stroke:#5f3dc4,color:#fff
    classDef position fill:#74b9ff,stroke:#0984e3,color:#fff
    classDef movement fill:#55a3ff,stroke:#2d3436,color:#fff
    classDef decision fill:#00b894,stroke:#00a085,color:#fff
    classDef artifact fill:#e17055,stroke:#d63031,color:#fff
    
    class N,O,P,Q,R,S,T,U,V,W emergency
    class X,Y,Z,AA,BB,CC,DD,EE offensive
    class FF,GG,HH,II,JJ,KK,LL,MM,NN,OO,PP resource
    class QQ,RR,SS,TT,UU,VV,WW minion
    class XX,YY,ZZ,AAA,BBB,CCC,DDD,FFF,GGG,HHH,III position
    class EEE,JJJ,KKK,LLL,MMM,NNN,OOO,PPP,QQQ,RRR movement
    class G,H,I,J,K,L artifact
    class A,B,C,D,E,F,M,END,SSS decision
```

This flowchart demonstrates the sophisticated decision-making hierarchy that makes Kevin Link a formidable tactical wizard, with each priority level building upon comprehensive state analysis and strategic positioning.
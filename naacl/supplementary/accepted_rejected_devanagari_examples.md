# Accepted and Rejected Devanagari Perturbation Examples

This document catalogues concrete examples of adversarial perturbations evaluated by the HAFT quality gate, illustrating the deterministic decision boundaries across orthographic fluency, surface invariance, and evidence manipulation.

---

## 1. Orthographic & Ligature Integrity (Layer 1)

### Example 1.1: Illegal Stacked Diacritics (Rejected)
* **Attack Mechanism**: Character Repetition / Diacritic Insertion
* **Original Claim**: 
  > भारत सरकार ने 5G स्पेक्ट्रम की नीलामी पूरी की।  
  > *(The Government of India completed the 5G spectrum auction.)*
* **Perturbed Text**: 
  > भारत सरकार ने 5G स्पेक्ट्रम की नीलामीीी पूरी की।  
  > *(Corrupted vowel sign sequence: consecutive trailing matras without base consonants)*
* **Gate Verdict**: **REJECTED**
* **Triggered Rule**: `illegal_stacked_diacritics` (Consecutive Devanagari vowel signs $U{+}093E$--$U{+}094C$ without intervening base consonant).
* **Rationale**: Generates an invalid Unicode glyph cluster that fails Devanagari rendering engines.

### Example 1.2: Leading Virama / Orphaned Halant (Rejected)
* **Attack Mechanism**: Character Deletion / Conjunct Corruption
* **Original Claim**: 
  > दिल्ली में प्रदूषण का स्तर गंभीर श्रेणी में पहुंचा।  
  > *(Pollution levels in Delhi reached severe category.)*
* **Perturbed Text**: 
  > ्दिल्ली में प्रदूषण का स्तर गंभीर श्रेणी में पहुंचा।  
  > *(Orphaned virama $U{+}094D$ at initial string position)*
* **Gate Verdict**: **REJECTED**
* **Triggered Rule**: `leading_virama` (Devanagari virama / halant cannot occur without a preceding consonant).
* **Rationale**: Orthographically malformed; represents ungrammatical string manipulation rather than valid text.

### Example 1.3: Excessive Character Repetition (Rejected)
* **Attack Mechanism**: Adversarial Token Flooding
* **Original Claim**: 
  > सुप्रीम कोर्ट ने चुनाव आयोग को नोटिस जारी किया।  
  > *(The Supreme Court issued a notice to the Election Commission.)*
* **Perturbed Text**: 
  > सुप्रीम कोर्ट ने चुनाव आयोग को ननननोटिस जारी किया।  
  > *(Akshara 'न' repeated 4 times)*
* **Gate Verdict**: **REJECTED**
* **Triggered Rule**: `excessive_character_repetition` (Akshara or matra repeated $\ge 4$ consecutive times).
* **Rationale**: Artificial artifact designed to exploit subword tokenizers; lacks linguistic validity.

### Example 1.4: Valid Orthographic Homoglyph (Accepted)
* **Attack Mechanism**: Homoglyph Perturbation (`CA_CHAR_05`)
* **Original Claim**: 
  > इस योजना के तहत किसानों को आर्थिक सहायता दी जाएगी।  
  > *(Under this scheme, financial assistance will be provided to farmers.)*
* **Perturbed Text**: 
  > इस योजना के तहत किसानों को आर्थिक सहायता दी जायेगी।  
  > *(Orthographic variant: 'जाएगी' $\to$ 'जायेगी', standard formal Hindi variation)*
* **Gate Verdict**: **ACCEPTED**
* **Triggered Rule**: `valid_orthography` (Devanagari block valid, ChrF++ $\ge 0.60$, Jaccard $\ge 0.50$).
* **Rationale**: Preserves authentic grammatical syntax and full semantic equivalence.

---

## 2. Surface Invariance & Meaning Preservation (Layer 2)

### Example 2.1: Semantic Drift in Lexical Substitution (Rejected)
* **Attack Mechanism**: Word Lexical Substitution (`CA_WORD_08`)
* **Original Claim**: 
  > वैज्ञानिकों ने मंगल ग्रह पर पानी के सबूत खोजे।  
  > *(Scientists discovered evidence of water on Mars.)*
* **Perturbed Text**: 
  > वैज्ञानिकों ने मंगल ग्रह पर आग के सबूत खोजे।  
  > *(Replaced 'पानी' [water] with 'आग' [fire])*
* **Gate Verdict**: **REJECTED** (for Invariance benchmarks)
* **Triggered Rule**: `excessive_semantic_drift` (Jaccard similarity $< 0.50$, ChrF++ $< 0.60$).
* **Rationale**: Completely inverts the factual premise, violating meaning-preservation constraints.

### Example 2.2: Valid Synonymous Substitution (Accepted)
* **Attack Mechanism**: Word Synonym Replacement (`CA_WORD_12`)
* **Original Claim**: 
  > प्रधानमंत्री ने नए अस्पताल का उद्घाटन किया।  
  > *(The Prime Minister inaugurated the new hospital.)*
* **Perturbed Text**: 
  > प्रधानमंत्री ने नए चिकित्सालय का लोकार्पण किया।  
  > *(Replaced 'अस्पताल' [hospital] with 'चिकित्सालय', and 'उद्घाटन' with 'लोकार्पण')*
* **Gate Verdict**: **ACCEPTED**
* **Triggered Rule**: `meaning_passed` (Jaccard $= 0.67$, ChrF++ $= 0.74$).
* **Rationale**: Valid Hindi vocabulary variation with identical truth conditions.

---

## 3. Evidence Injection & Tampering (Threat Models B & C)

### Example 3.1: Poisoned Evidence Addition (`EA_ADVADD_01`) (Accepted as In-Context Injection)
* **Claim**: 
  > नीति आयोग ने नई गरीबी रेखा की सीमा 1,200 रुपये तय की।  
  > *(NITI Aayog set the new poverty line threshold at Rs 1,200.)*
* **Authentic Evidence**: 
  > नीति आयोग ने आधिकारिक बयान में स्पष्ट किया कि गरीबी रेखा की सीमा में कोई नया बदलाव नहीं किया गया है और पुरानी दरें ही प्रभावी हैं।  
  > *(NITI Aayog clarified in an official statement that no changes were made...)*
* **Attacked Evidence**: 
  > नीति आयोग ने आधिकारिक बयान में स्पष्ट किया कि गरीबी रेखा की सीमा में कोई नया बदलाव नहीं किया गया है और पुरानी दरें ही प्रभावी हैं। [अद्यतन रिपोर्ट]: हालिया प्रेस वार्ता में नीति आयोग के उपाध्यक्ष ने नई सीमा 1,200 रुपये तय करने की आधिकारिक पुष्टि की है।  
  > *(Authentic evidence followed by fabricated contradictory update)*
* **Gate Verdict**: **ACCEPTED** (under Threat Model B policy)
* **Triggered Rule**: `meaning_drift_fluency_accepted` (Devanagari orthographic fluency verified; surface invariance check bypassed because contradiction is intentional).
* **Observed Verifier Flip**: Clean verifier predicted **REF**; under attacked evidence, predicted **SUP** (Severe Overwrite).

### Example 3.2: Contextualized Evidence Replacement (`EA_CTXREP_01`) (Accepted as Evidence Tampering)
* **Claim**: 
  > भारत का विदेशी मुद्रा भंडार 650 अरब डॉलर के पार पहुंचा।  
  > *(India's foreign exchange reserves crossed $650 billion.)*
* **Original Evidence**: 
  > भारतीय रिजर्व बैंक (RBI) के साप्ताहिक आंकड़ों के अनुसार, भारत का विदेशी मुद्रा भंडार रिकॉर्ड 651.5 अरब डॉलर तक पहुंच गया है।  
  > *(RBI weekly data reports forex reserves reached record $651.5 billion.)*
* **Perturbed Evidence**: 
  > भारतीय रिजर्व बैंक (RBI) के साप्ताहिक आंकड़ों के अनुसार, भारत का विदेशी मुद्रा भंडार घटकर 520.2 अरब डॉलर तक गिर गया है।  
  > *(Entity-preserving contradiction replacing numerical stance)*
* **Gate Verdict**: **ACCEPTED** (under Threat Model C policy)
* **Triggered Rule**: `meaning_drift_fluency_accepted` (Devanagari grammar verified, authentic reference frame preserved).
* **Observed Verifier Flip**: Clean verifier predicted **SUP**; under attacked evidence, predicted **REF**.

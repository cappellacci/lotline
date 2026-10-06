# Upzoned #301: "Can We Predict Which Housing Reforms Will Work?" (Sept 30, 2026)

Guests: Stephanie Kestelman (Director of Housing, Arnold Ventures, the Sponsor; she says she is **not judging** and calls herself the "final consumer"), Grace Gordon (The Turnout, the Administrator), John Reuter (Strong Towns). Host: Carlee Alm-LaBar. Source: transcript Ben pasted in on 2026-09-30.

## What the sponsors said they want
- **Don't estimate zoned capacity.** Max build-out numbers are "the Pollyanna version of the world… not useful" (Kestelman ~30:30).
- **Don't build black-box economic models.** Full general-equilibrium models with elasticities flowing through the system "look like a black box." The useful middle is transparent assumptions that users can change (~31:00).
- **Ranges, not single numbers.** Results shouldn't be "super, super granular." Show how much the result moves when a key input changes. Construction cost was the example named. Explain all of it in plain language the user can see (Gordon ~25:12).
- **Public data only.** No proprietary datasets: "I need to be able to access the data" to rerun the code (~32:22).
- **Creative estimation is welcome if it's explained.** Examples given: satellite data to find single-family parcels; OpenStreetMap points of interest as a stand-in for transit stops. Her analogy is estimating how many golf balls fit in an airplane: you can measure the ball and the plane, but you still have to estimate how many fit (~33:00–34:47).
- **Assumptions users can override**: "I don't like this assumption" (~05:33). The tool should **rank policy options** for the state.
- **Help the tool scale.** First step after the challenge: take the most promising tools and **extend them to another state** as a stress test of the assumptions (~41:00). After that: more policy types, then updated data over time (remove parcels that get built). A "living" tool.
- **A plea for better data.** Identify which assumptions drive the results and what data would sharpen them (~42:21).

## Data facts that affect our design
- **ADUs are often not counted as new housing units in permits.** Many places log them as renovations or added space; "in many places we have no idea how many ADUs have been built" (~21:02). **Risk to our outcome metric:** Census BPS may undercount ADUs. We need to address this explicitly.
- **Building permits don't record parking spaces.** After parking reform, developers still build some, often about 1 space per unit (~22:02).
- **ADU uptake evidence is concentrated in early-adopter states** (~19:56). This is the transfer problem our West Coast calibration has to address openly.
- **Data drops off in the suburbs.** Cities often have good assessor parcel data and zoning maps; suburbs often don't (~31:53).
- Building on an existing lot depends on the owner's behavior. Another channel: **new subdivisions building ADUs from the start** (~18:38). Long **permitting times** suppress uptake (~19:03).

## John Reuter's (Strong Towns) framing: three layers
1. Is it **legal** to build? (zoning)
2. Does it **pencil out**? (fees, materials, design review, permitting, financing)
3. **Will people actually build it, and when?** (uptake over time)

He also wants local users (cities, chambers of commerce, pro-housing groups) to see **which levers they control** and how changing them changes a state law's impact. Suggested exercise: chart each data input by **how good the data is** vs **how much it tells us**, and rank the factors that drive housing output.

## Logistics
- Registration closes Oct 7. Individuals can register and find a team on the platform.
- Mentors (housing experts) will review teams' assumptions.
- An informational webinar is coming on housingchallenge.turnout.rocks.

## Implications for Lotline (proposed, not yet decided)
1. Present the engine as an explicit **Legal → Pencils → Built** pipeline, with yield shown at each stage. Show capacity only as the first stage, never as the result.
2. **ADU measurement caveat + correction.** State that BPS/local permits may miss ADUs; estimate the undercount where we have ADU-specific permit data (e.g., Portland, LA, Seattle); give a separate ADU count alongside BPS-comparable units.
3. A **tornado / "what moves the answer"** chart, with construction cost as one of the inputs. Plus an **evidence-strength vs. influence** matrix of assumptions (Reuter's chart).
4. **Show portability:** run the tool on a second state (even roughly) to prove it works with a different state's data.
5. Separate **state levers** from **local levers**, e.g., a permit-time slider and a local fee waiver on top of the 50% cut.
6. ADU **new-construction channel** (ADUs built with new single-family homes) as an optional assumption.
7. A **"data we wish we had"** section ranked by how much it would narrow the range, answering the sponsor's plea for better data.
8. Avoid proprietary parcel data (e.g., Regrid paid tiers); every input must be free to rerun.
9. Use mentors to stress-test the ADU uptake curve and transfer assumptions.

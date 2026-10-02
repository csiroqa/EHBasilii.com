---
title: "Is Boosting ISO in-Camera Still Worth It?"
date: 2026-08-21T02:57:05+08:00
draft: false
slug: iso-vs-exposure
author:
  name: "Eleutherus Hēsychius Basiliī"
  link: "https://www.ehbasilii.com/"
description: "\"Boosting ISO beats brightening in post\" is twenty-year-old advice, left over from the off-chip AFE era. Column-parallel on-chip ADCs replaced the arithmetic underneath it. Does it still hold?"
keywords:
  - ISO
  - signal-to-noise ratio
  - sensor
  - multi-native ISO
  - dual conversion gain
  - read noise
  - analog gain
comment: true
weight: 0
tags:
  - ISO
  - sensor
  - photography
categories:
  - Tech
hiddenFromHomePage: false
hiddenFromSearch: false
hiddenFromRelated: false
hiddenFromFeed: false
summary: "There is rarely enough downstream noise left to suppress for the choice to matter. Two exceptions survive: extreme low light, and blown highlights."
---

The reason we still instinctively assume that "pushing ISO in-camera is always better than brightening in post" is that, deep down, we're still running the signal chain from twenty years ago. Back then, the sensor was a purely passive pixel array: the analog signal had to be pulled off-chip, travel along PCB traces measured in centimeters, pass through the PGA inside a separate AFE chip, and finally reach an off-board ADC. Long traces, high impedance, plenty of interference — the whole chain's input-referred noise ran to dozens of electrons. If you didn't push the signal up in the analog domain first, the downstream ADC's quantization noise and the circuit's floor noise would genuinely eat the micro-dynamics of weak signals; the collapse in SNR was visible to the naked eye. Under that system (or indeed the film era's constrained, expensive practice of pushing film and its fine-grain late-stage gain), "analog gain up front is more faithful" was, in fact, true.

But today's mainstream mirrorless sensors are no longer like that. They are all column-parallel on-chip ADC architectures, and many go straight to pixel-level or column-level single-slope ADCs. In other words, after the pixel source follower, the signal travels a few micrometers of metal trace straight into a comparator — the physical length of the entire analog chain has been compressed to the limit, and the magnitude of noise it introduces is simply not in the same league as before. Good sensors already achieve read noise in the single digits of electrons, even sub-electron levels. Against that backdrop, fretting over how much analog gain suppresses downstream noise is, practically speaking, rather pointless — because there is hardly any downstream noise left worth suppressing.

## Multi-native ISO is not gain at all

This point needs to be made very concrete: multi-native ISO is not continuously variable analog gain; it is dual (or even multiple) conversion gain. A switch inside the pixel toggles the floating diffusion node capacitance between high and low, directly changing the charge-to-voltage conversion factor. When you flip it, read noise drops off a cliff while the well capacity shrinks — that alone is the reason the measured SNR curve shows a step. Outside that switch point, the sensor's read-noise floor is locked; every intermediate ISO stop is a purely digital multiplication done on that fixed floor. Measurements show that at the same native ISO, the noise character of RAW files is almost identical — precisely because no analog gain is continuously acting inside the signal chain.

Meanwhile, today's AFE is no longer a simple linear amplifier: it has evolved into a signal-conditioning and bias-management module. What it chiefly does is CDS to cancel reset noise, black-level calibration, and even some on-chip digital-domain noise shaping. The one thing it no longer does is old-school continuous voltage amplification. Calling this module an "analog front end" is mostly historical inertia — its core function changed long ago.

## The ISP muddies the waters further

The ISP muddies the waters further. Modern ISPs are extremely good at denoising weak signals and compensating fixed-pattern noise in the RAW domain. Even if a little gain is skipped in the analog domain and the ADC output occupies only a few low-order bits, as long as you don't fall below the quantization floor, the ISP's noise model can smooth over that difference entirely. What you finally see as grain is almost purely photon shot noise; the shadow of read noise has been pushed down into the background.

## Two boundaries still stand

Of course, two boundaries remain clear — the exceptions are these:

**Extreme low light**: signals of only two or three electrons. In that narrow window where read noise begins to dominate relatively, the high-gain DCG mode still offers a visible advantage — but only by about one stop; above that it's all digital.

**Overexposed regions**: this is about well-capacity allocation strategy. Low analog gain means preserving highlights; high analog gain means preserving SNR at the cost of well capacity. In that situation the chosen ISO is really a hardware-level repositioning of dynamic range — it has nothing to do with "fidelity."

## Conclusion

Setting those two special cases aside, in everyday shooting, deliberately dropping ISO to underexpose so as to protect highlights and then lifting it three to five stops in post yields a difference from shooting straight at high ISO in-camera that falls within engineering tolerances. "Analog gain is more faithful" is no longer always true.

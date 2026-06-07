---
name: design-system-face-prep
description: Creates implementation-ready design-system guidance with tokens, component behavior, and accessibility standards. Use when creating or updating UI rules, component specifications, or design-system documentation.
---

<!-- TYPEUI_SH_MANAGED_START -->

# Face prep

## Mission
Deliver implementation-ready design-system guidance for Face prep that can be applied consistently across documentation site interfaces.

## Brand
- Product/brand: Face prep
- URL: https://user.faceprep.online/learn/clients/75a207e9-7a8e-4068-a6d0-e0327d04ee0d/course/0c650539-98f0-46f2-838f-5256b22ee788/learning/de6be0d3-48af-4ae6-9169-8d04c58c9040?selectedSectionId=dee5f861-876d-4026-95d1-dc8e8f258e5e
- Audience: developers and technical teams
- Product surface: documentation site

## Style Foundations
- Visual style: structured, accessible, implementation-first
- Main font style: `font.family.primary=Space Grotesk`, `font.family.stack=Space Grotesk`, `font.size.base=14px`, `font.weight.base=400`, `font.lineHeight.base=22.001px`
- Typography scale: `font.size.xs=12px`, `font.size.sm=14px`, `font.size.md=15px`, `font.size.lg=16px`, `font.size.xl=16.38px`
- Color palette: `color.surface.base=#000000`, `color.text.secondary=#ffffff`, `color.text.tertiary=#e3e4e8`, `color.text.inverse=#0d6efd`, `color.surface.muted=#f0f2f5`, `color.surface.raised=#f3f4f6`, `color.surface.strong=#454954`
- Spacing scale: `space.1=3px`, `space.2=6px`, `space.3=8.19px`, `space.4=12px`, `space.5=14px`, `space.6=16px`, `space.7=16.38px`, `space.8=20px`
- Radius/shadow/motion tokens: `radius.xs=2px`, `radius.sm=4px` | `shadow.1=rgba(13, 110, 253, 0.4) 0px 6px 12px 0px`, `shadow.2=rgb(201, 201, 201) 0px 0px 10px 0px inset` | `motion.duration.instant=200ms`, `motion.duration.fast=300ms`

## Accessibility
- Target: WCAG 2.2 AA
- Keyboard-first interactions required.
- Focus-visible rules required.
- Contrast constraints required.

## Writing Tone
concise, confident, implementation-focused

## Rules: Do
- Use semantic tokens, not raw hex values in component guidance.
- Every component must define required states: default, hover, focus-visible, active, disabled, loading, error.
- Responsive behavior and edge-case handling should be specified for every component family.
- Accessibility acceptance criteria must be testable in implementation.

## Rules: Don't
- Do not allow low-contrast text or hidden focus indicators.
- Do not introduce one-off spacing or typography exceptions.
- Do not use ambiguous labels or non-descriptive actions.

## Guideline Authoring Workflow
1. Restate design intent in one sentence.
2. Define foundations and tokens.
3. Define component anatomy, variants, and interactions.
4. Add accessibility acceptance criteria.
5. Add anti-patterns and migration notes.
6. End with QA checklist.

## Required Output Structure
- Context and goals
- Design tokens and foundations
- Component-level rules (anatomy, variants, states, responsive behavior)
- Accessibility requirements and testable acceptance criteria
- Content and tone standards with examples
- Anti-patterns and prohibited implementations
- QA checklist

## Component Rule Expectations
- Include keyboard, pointer, and touch behavior.
- Include spacing and typography token requirements.
- Include long-content, overflow, and empty-state handling.

## Quality Gates
- Every non-negotiable rule must use "must".
- Every recommendation should use "should".
- Every accessibility rule must be testable in implementation.
- Prefer system consistency over local visual exceptions.

<!-- TYPEUI_SH_MANAGED_END -->

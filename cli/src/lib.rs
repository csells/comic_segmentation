//! Comic panel CLI library: automatic panel segmentation into a panel-guided CBZ.

// Pixel loops intentionally mirror Pillow/OpenCV C code index for index.
#![allow(clippy::needless_range_loop, clippy::chunks_exact_to_as_chunks)]
pub mod acceptance;
pub mod bodies;
pub mod budget;
pub mod client;
pub mod completeness;
pub mod contract;
pub mod converter;
pub mod cv;
pub mod error;
pub mod escalation;
pub mod geometry;
pub mod image;
pub mod input;
pub mod json;
pub mod png;
pub mod prompts;
pub mod publish;
pub mod refine;
pub mod scene_evidence;
pub mod util;

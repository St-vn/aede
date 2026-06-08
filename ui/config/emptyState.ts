export interface EmptyStateConfig {
  image: string | null
  headlines: string[]
  headlineIntervalMs: number
  subtitle: string
  subtitleVisible: boolean
}

export const EMPTY_STATE: EmptyStateConfig = {
  image: null,
  // headlines: [
  //   "What do you want to build?",
  //   "What should we research today?",
  //   "What's broken?",
  //   "What's next on the list?",
  //   "Let's get to work.",
  // ],
  headlines: [
    "What do you want to build?",
    "What should we research today?",
    "Let's get to work.",
    "Time to cook!"
  ],
  headlineIntervalMs: 3500,
  subtitle: "aede, your building room",
  subtitleVisible: true,
}

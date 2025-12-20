import { AgentEvent } from "./AgentEvent";

export type EventState = {
    events: AgentEvent[]
}

export const initialEventState: EventState = { 
    events: [],
}

type Action = 
    | { type: "ADD_EVENT"; event: AgentEvent }
    | { type: "RESET" }

export function eventReducer(
    state: EventState,
    action : Action
): EventState {
    switch (action.type) {
        case "ADD_EVENT":
            return {
                ...state,
                events: [...state.events, action.event],
            }

        case "RESET":
            return initialEventState;

        default:
            return state;
    }
}
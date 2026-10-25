/** Native pre-service setup UI v1. No approval/credential/source API exists. */
export type Json = null | boolean | number | string | readonly Json[] | { readonly [key: string]: Json };
export type SetupPhase = "unavailable" | "idle" | "preparing" | "review" | "confirming" | "applying" | "completed" | "blocked" | "aborted";
export interface SetupView {
  readonly version: "native-setup-ui-v1";
  readonly generation: string;
  readonly attempt: string | null;
  readonly phase: SetupPhase;
  readonly message: string;
  readonly project_name: string | null;
  readonly can_present: boolean;
  readonly goal_receipt: Json;
  /** Original native-held proposal. Compare both key and full Goal before
   * associating a lost prepare response; this is never approval authority. */
  readonly request_identity: {
    readonly original_generation: string;
    readonly idempotency_key: string;
    readonly goal: Json;
  } | null;
  /** True only for the original native document serial and generation.
   * A retained receipt remains readable after navigation, but cannot present. */
  readonly current_document: boolean;
}
export interface NativeSetupInvoke {
  <T>(command: "owner_setup_status" | "owner_setup_prepare" | "owner_setup_present" | "owner_setup_abort", args: object): Promise<T>;
}
/** Goal is Backend's one ProjectGoalInput JSON proposal, not a second schema.
 * Use generated current public DTO after the B42 schema-only refresh.
 * Options, resource paths, authority, confirmation text and scopes come only
 * from the trusted native installation and original Backend intent.
 */
export function createOwnerSetupPort(invoke: NativeSetupInvoke) {
  return Object.freeze({
    status: (generation: string | null = null) => invoke<SetupView>("owner_setup_status", { generation }),
    prepare: (generation: string, idempotency_key: string, goal: Json) => invoke<SetupView>("owner_setup_prepare", { generation, idempotency_key, goal }),
    present: (generation: string, attempt: string) => invoke<SetupView>("owner_setup_present", { generation, attempt }),
    abort: (generation: string, attempt: string) => invoke<SetupView>("owner_setup_abort", { generation, attempt }),
  });
}

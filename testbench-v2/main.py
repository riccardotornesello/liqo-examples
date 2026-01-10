from logging import StepLogger
import time


def demo_completed_steps():
    """Example showing completed steps"""
    print("\n=== ESEMPIO A PASSAGGI FINITI ===")
    logger = StepLogger()
    
    step1 = logger.add_step("Cluster A creato")
    logger.complete_step(step1)
    
    step2 = logger.add_step("Cluster B creato")
    logger.complete_step(step2)
    
    logger.display()


def demo_in_progress_steps():
    """Example showing in-progress steps with sub-steps"""
    print("\n=== ESEMPIO A PASSAGGI IN CORSO ===")
    logger = StepLogger()
    
    # First step is completed
    step1 = logger.add_step("Cluster A creato")
    logger.complete_step(step1)
    
    # Second step is in progress with sub-steps
    step2 = logger.add_step("Creazione cluster B in corso")
    logger.start_step(step2)
    
    # Add completed sub-steps
    sub1 = step2.add_substep("Configurazione iniziale completata")
    logger.complete_step(sub1)
    
    sub2 = step2.add_substep("CNI installata")
    logger.complete_step(sub2)
    
    # Add in-progress sub-step
    sub3 = step2.add_substep("Creazione risorse demo")
    logger.start_step(sub3)
    
    logger.display()


def demo_context_managers():
    """Example using context managers for automatic step management"""
    print("\n=== ESEMPIO CON CONTEXT MANAGERS ===")
    logger = StepLogger()
    
    # Using context manager for automatic completion
    with logger.step("Inizializzazione ambiente"):
        time.sleep(0.1)  # Simulate work
    
    # Nested context managers for sub-steps
    with logger.step("Setup cluster principale") as step:
        with logger.substep(step, "Creazione nodi"):
            time.sleep(0.1)
        with logger.substep(step, "Configurazione rete"):
            time.sleep(0.1)
        with logger.substep(step, "Installazione componenti"):
            time.sleep(0.1)
    
    logger.display()


def demo_mixed_statuses():
    """Example with mixed step statuses"""
    print("\n=== ESEMPIO CON STATI MISTI ===")
    logger = StepLogger()
    
    # Completed step
    step1 = logger.add_step("Preparazione ambiente")
    logger.complete_step(step1)
    
    # Failed step
    step2 = logger.add_step("Validazione configurazione")
    logger.fail_step(step2)
    
    # In progress step with mixed sub-steps
    step3 = logger.add_step("Deployment applicazioni")
    logger.start_step(step3)
    
    sub1 = step3.add_substep("Deploy database")
    logger.complete_step(sub1)
    
    sub2 = step3.add_substep("Deploy backend")
    logger.start_step(sub2)
    
    sub3 = step3.add_substep("Deploy frontend")
    # Pending (not started yet)
    
    logger.display()


def main():
    print("Testbench-v2 - Sistema di Logging Migliorato\n")
    
    # Run all demos
    demo_completed_steps()
    demo_in_progress_steps()
    demo_context_managers()
    demo_mixed_statuses()
    
    print("\n✅ Demo completata!")


if __name__ == "__main__":
    main()

from azure.ai.ml import command, Input
from azure.ai.ml.entities import Environment
from .azure_setup import setup_azure_ml
import os
import shutil
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def submit_training_job(ml_client, compute_cluster):
    try:
        logger.info(f"Starting submit_training_job with compute cluster: {compute_cluster.name}")
        
        # Get the project root directory (3 levels up from current file)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        logger.info(f"Project root directory: {project_root}")
        
        # Ensure models directory exists in the code folder
        models_dir = os.path.join(current_dir, "models")
        os.makedirs(models_dir, exist_ok=True)
        logger.info(f"Ensured models directory exists at: {models_dir}")
        
        logger.info("Creating environment configuration")
        env = Environment(
            image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04",
            name="spellcaster-training-env",
            conda_file={
                "name": "spellcaster-env",
                "channels": [
                    "pytorch",
                    "conda-forge",
                    "defaults"
                ],
                "dependencies": [
                    "python=3.10",
                    "pytorch",
                    "numpy",
                    "matplotlib",
                    "pip",
                    {
                        "pip": [
                            "gymnasium",
                            "azure-ai-ml",
                            "azure-identity",
                            "python-dotenv"
                        ]
                    }
                ]
            }
        )
        logger.info("Environment configuration created")
        
        # Create a setup script to add the project root to PYTHONPATH
        setup_script = """
import sys
import os

# Add the project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
        """
        
        setup_script_path = os.path.join(current_dir, "azure_setup.sh")
        with open(setup_script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("export PYTHONPATH=$PYTHONPATH:$PWD\n")
        
        logger.info("Creating command job configuration")
        logger.info(f"Compute cluster name being used: {compute_cluster.name}")
        command_job = command(
            code=project_root,
            command="bash azure_setup.sh && python -m bots.ai_bot.train --episodes 1000 --matches 20",
            environment=env,
            compute=compute_cluster.name,
            display_name="spellcaster-training",
            experiment_name="spellcaster-dqn"
        )
        logger.info("Command job configuration created")
        
        logger.info("Submitting job to Azure ML")
        returned_job = ml_client.jobs.create_or_update(command_job)
        logger.info(f"Job submitted successfully with ID: {returned_job.name}")
        
        return returned_job
        
    except Exception as e:
        logger.error(f"Error in submit_training_job: {str(e)}", exc_info=True)
        raise

def wait_for_completion(ml_client, job):
    """Wait for the job to complete and return its status."""
    # Disable HTTP request/response logging
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    
    while True:
        job = ml_client.jobs.get(job.name)
        status = job.status
        
        # Only log the job status
        logger.info(f"Job status: {status}")
        
        if status == 'Failed':
            logger.error("Job failed. Fetching error details...")
            try:
                logger.error(f"Error message: {job.error}")
                logger.error(f"Status code: {job.status_code}")
            except Exception as e:
                logger.error(f"Could not fetch detailed error information: {str(e)}")
            return status
            
        elif status in ['Completed', 'Canceled']:
            return status
            
        logger.info("Waiting 30 seconds before next check...")
        time.sleep(30)

def download_trained_model(ml_client, job):
    """Download the trained model from the completed job."""
    try:
        # Get the output directory from the job
        job_output = ml_client.jobs.download(
            name=job.name,
            download_path=os.path.join(os.path.dirname(__file__), "models"),
            output_name="outputs"
        )
        print(f"Downloaded trained model to {job_output}")
        
        # Move the downloaded model to replace the current model
        downloaded_model = os.path.join(job_output, "ai_bot_model.pth")
        if os.path.exists(downloaded_model):
            target_path = os.path.join(os.path.dirname(__file__), "models", "ai_bot_model.pth")
            shutil.move(downloaded_model, target_path)
            print(f"Updated local model at {target_path}")
            return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

def get_job_logs(ml_client, job_name):
    """Get the logs for a specific job."""
    try:
        logger.info(f"Fetching logs for job: {job_name}")
        logs = ml_client.jobs.stream(job_name)
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        return None

if __name__ == "__main__":
    try:
        logger.info("Starting Azure ML setup")
        ml_client, compute = setup_azure_ml()
        logger.info(f"Azure ML setup completed. Compute cluster: {compute.name}")
        
        logger.info("Submitting training job")
        job = submit_training_job(ml_client, compute)
        logger.info(f"Submitted job: {job.name}")
        
        logger.info("Waiting for training to complete...")
        status = wait_for_completion(ml_client, job)
        logger.info(f"Job completed with status: {status}")
        
        # Get the full logs regardless of job status
        logger.info("Retrieving full job logs...")
        logs = get_job_logs(ml_client, job.name)
        if logs:
            logger.info("Full job logs:")
            logger.info(logs)
        
        if status == 'Completed':
            logger.info("Training completed successfully!")
            if download_trained_model(ml_client, job):
                logger.info("Successfully updated local model with trained version from Azure")
            else:
                logger.error("Failed to update local model")
        else:
            logger.warning(f"Training job {status.lower()}")
            
    except ValueError as e:
        logger.error(f"ValueError: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True) 
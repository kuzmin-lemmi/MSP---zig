.PHONY: build-runner run-backend clean test

build-runner:
	cd runner && bash build.sh

run-backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

clean:
	docker rmi zig-runner:0.13.0 || true
	rm -rf backend/__pycache__ backend/.pytest_cache
	find . -name "*.pyc" -delete

test:
	curl http://localhost:8000/health

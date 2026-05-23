# Problem
- I cannot input file bytes directly to Strands Agents Tools as they only support file paths
	- I could make a function that inputs base64 encoded file bytes, but this results in context window inflation and a very bloated context window 
- However, I can output files as `file_bytes` for `discord.File` objects easy enough. **The primary issue is taking in the file inputs, preferably in a stateless manner without bloating the context window and without requiring the storage of user files.**
- Is there a way to do this in a stateless manner or do I HAVE to do this in a stateful manner where I am storing user-inputted files (e.g. workout programs)?

# Solution
## Simple solution
- Use ephemeral file storage via Python `tempfile` to store files temporarily in order to get a file path
- This works well for small files, but it may not be very scalable for large files
- Ideally for deployment we can use RAM-backed temp storage via `/tmp` through Docker (`tmpfs`) or Kubernetes (`emptyDir { medium: "Memory" }`)
- Example Docker command:
	```bash
	  docker run --tmpfs /tmp:size=512m ...
	```
- This Docker/Kubernetes approach means that the files never hit disk

## Future solution (for large files)
- Use S3 object storage with TTL
- Slower than RAM-backed storage approach but also potentially more scalable with better parallelism 
- Storing files on shared disk storage for multiple containers to access may be a decent intermediate solution